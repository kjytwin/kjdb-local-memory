"""Bounded native text memory. No model, network, or automatic capture."""
import ctypes as ct
import hashlib
import json
import os
import time
import unicodedata
import uuid
from pathlib import Path

NAMES = ["ok","invalid","io_error","corrupt","busy","limit","conflict",
         "degraded","recovery_required","outcome_unknown","no_memory"]
class MemoryError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(NAMES[code] if 0 <= code < len(NAMES) else "native_error")

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
def text(value, name, limit, empty=False):
    if type(value) is not str or (not value and not empty) or "\0" in value:
        raise ValueError("invalid " + name)
    if len(value.encode("utf-8")) > limit:
        raise ValueError(name + " exceeds byte limit")
    return value
def normalized(value):
    return unicodedata.normalize("NFC", value).casefold()

def identifier(value):
    if type(value) is not str:
        raise ValueError("UUID must be a string")
    if str(uuid.UUID(value)) != value:
        raise ValueError("UUID must use canonical lowercase format")
    return value

class MemoryStore:
    def __init__(self, library, directory, project_id):
        self.project = text(project_id, "project_id", 64)
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        library_path = Path(library)
        # Windows app containers can read/load an explicitly supplied DLL while
        # denying GetFinalPathNameByHandle used by Path.resolve(). Keep the
        # operator-selected absolute path; do not search PATH for a library.
        if os.name == 'nt':
            library_path = library_path.absolute()
            if not library_path.is_file() or library_path.is_symlink():
                raise ValueError('Native library must be an existing regular file')
        else:
            library_path = library_path.resolve(strict=True)
        self.lib = ct.CDLL(str(library_path))
        self.lib.kjm_open.argtypes = [ct.c_char_p, ct.POINTER(ct.c_void_p)]
        self.lib.kjm_put.argtypes = [ct.c_void_p, ct.c_char_p, ct.c_void_p,
                                    ct.c_void_p, ct.c_size_t, ct.POINTER(ct.c_uint64), ct.POINTER(ct.c_int)]
        self.lib.kjm_read.argtypes = [ct.c_void_p, ct.c_uint64, ct.c_void_p,
                                     ct.c_size_t, ct.POINTER(ct.c_size_t), ct.c_void_p, ct.c_void_p]
        self.lib.kjm_state.argtypes = [ct.c_void_p, ct.POINTER(ct.c_uint64),
                                      ct.POINTER(ct.c_uint64), ct.POINTER(ct.c_int), ct.POINTER(ct.c_int)]
        self.lib.kjm_close.argtypes = [ct.c_void_p]
        self.lib.kjm_close.restype = None
        self.lib.kjm_recover_uncommitted_tail.argtypes = [ct.c_void_p]
        self.lib.kjm_backup.argtypes = [ct.c_void_p, ct.c_char_p]
        self.handle = ct.c_void_p()
        self._unknown = False
        self._check(self.lib.kjm_open(str(self.directory).encode(), ct.byref(self.handle)))
        self.memories = {}
        self.requests = {}
        self._search_text = {}
        try:
            for seq in range(1, self.status()["committed_operations"] + 1):
                record, request, digest = self._read(seq)
                self._apply(record, request, digest, seq)
        except Exception:
            self.close()
            raise

    def _check(self, code):
        if code:
            if code == 9:
                self._unknown = True
            raise MemoryError(code)
    def close(self):
        if self.handle:
            self.lib.kjm_close(self.handle)
            self.handle = ct.c_void_p()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    def _scope(self, project):
        if project != self.project:
            raise PermissionError("project scope mismatch")
    def _read(self, seq):
        payload = ct.create_string_buffer(16384)
        length = ct.c_size_t()
        request = ct.create_string_buffer(37)
        digest = ct.create_string_buffer(32)
        self._check(self.lib.kjm_read(self.handle, seq, payload, len(payload),
                                     ct.byref(length), request, digest))
        return json.loads(payload.raw[:length.value]), request.value.decode(), digest.raw
    def _apply(self, r, request, digest, seq):
        required = {"schema","operation","memory_id","project_id","version","request_id",
                    "created_at_ns","updated_at_ns","data"}
        if type(r) is not dict or set(r) != required or type(r["schema"]) is not int or r["schema"] != 1 or r["request_id"] != request:
            raise MemoryError(3)
        try:
            identifier(r["memory_id"])
            text(r["project_id"], "project_id", 64)
        except (ValueError, TypeError):
            raise MemoryError(3) from None
        if any(type(r[k]) is not int or r[k] <= 0 for k in ("created_at_ns","updated_at_ns")):
            raise MemoryError(3)
        old = self.memories.get(r["memory_id"])
        if old and r["created_at_ns"] != old["created_at_ns"]:
            raise MemoryError(3)
        if type(r["version"]) is not int or r["version"] != (old["version"]+1 if old else 1):
            raise MemoryError(3)
        if old and (old["project_id"] != r["project_id"] or old["operation"] == "delete"):
            raise MemoryError(3)
        if r["operation"] not in ("put","delete") or (r["operation"] == "delete" and old is None):
            raise MemoryError(3)
        if r["operation"] == "put":
            try: self._validate_data(r["data"])
            except (ValueError, TypeError, KeyError): raise MemoryError(3) from None
        elif r["data"] is not None:
            raise MemoryError(3)
        self.memories[r["memory_id"]] = r
        if r["operation"] == "put":
            self._search_text[r["memory_id"]] = (
                normalized(r["data"]["title"]), normalized(r["data"]["text"]))
        else:
            self._search_text.pop(r["memory_id"], None)
        self.requests[request] = {"digest":digest, "project":r["project_id"],
            "response":{"memory_id":r["memory_id"],"version":r["version"],
                        "committed":True,"duplicate":False,
                        "logical_deleted":r["operation"]=="delete","sequence":seq}}
    def status(self):
        count, end = ct.c_uint64(), ct.c_uint64()
        degraded, tail = ct.c_int(), ct.c_int()
        self._check(self.lib.kjm_state(self.handle,ct.byref(count),ct.byref(end),
                                      ct.byref(degraded),ct.byref(tail)))
        return {"committed_operations":count.value,"committed_bytes":end.value,
                "active_memories":sum(r["operation"]=="put" and r["project_id"]==self.project
                                      for r in getattr(self,"memories",{}).values()),
                "metadata_degraded":bool(degraded.value),"uncommitted_tail":bool(tail.value),
                "outcome_unknown":self._unknown,"max_log_bytes":33554432,
                "max_operations":8192,"max_active_memories":1000}
    def recover_uncommitted_tail(self):
        """Explicit operator action, not exposed as an agent tool."""
        self._check(self.lib.kjm_recover_uncommitted_tail(self.handle))
    def backup(self, path):
        """Trusted operator path; refuses overwrite. Not an agent tool."""
        # A failed backup makes the destination uncertain, not the source.
        code = self.lib.kjm_backup(self.handle,str(path).encode())
        if code:
            raise MemoryError(code)
    @staticmethod
    def _validate_data(d):
        if type(d) is not dict or set(d) != {"title","text","tags","kind","source","conversation_id","content_sha256"}:
            raise ValueError("invalid memory data")
        text(d["title"],"title",256,True)
        text(d["text"],"text",8192)
        text(d["source"],"source",256)
        text(d["conversation_id"],"conversation_id",128,True)
        if d["kind"] not in ("note","fact","decision","task"):
            raise ValueError("invalid kind")
        if type(d["tags"]) is not list or len(d["tags"])>8:
            raise ValueError("invalid tags")
        for tag in d["tags"]:text(tag,"tag",64)
        if d["content_sha256"] != hashlib.sha256(d["text"].encode()).hexdigest():
            raise ValueError("content hash mismatch")
    def _existing_request(self, request, digest):
        found=self.requests.get(request)
        if found is None:return None
        if found["project"] != self.project or found["digest"] != digest:
            raise MemoryError(6)
        return dict(found["response"],duplicate=True)
    def _commit(self, record, request, digest):
        raw=canonical(record)
        if len(raw)>16384:raise ValueError("record exceeds byte limit")
        seq,duplicate=ct.c_uint64(),ct.c_int()
        self._check(self.lib.kjm_put(self.handle,request.encode(),digest,raw,len(raw),
                                    ct.byref(seq),ct.byref(duplicate)))
        if duplicate.value:
            return dict(self.requests[request]["response"],duplicate=True)
        self._apply(record,request,digest,seq.value)
        return dict(self.requests[request]["response"])
    def remember(self, project_id, request_id, text_value, title="", tags=None,
                 kind="note", source="manual", conversation_id="",
                 memory_id=None, expected_version=None):
        self._scope(project_id);identifier(request_id)
        tags=[] if tags is None else tags
        data={"title":title,"text":text_value,"tags":tags,"kind":kind,"source":source,
              "conversation_id":conversation_id,
              "content_sha256":hashlib.sha256(text(text_value,"text",8192).encode()).hexdigest()}
        self._validate_data(data)
        if (memory_id is None) != (expected_version is None):
            raise ValueError("update requires memory_id and expected_version")
        if memory_id is not None:
            identifier(memory_id)
            if type(expected_version) is not int or expected_version<1:
                raise ValueError("invalid expected_version")
        request={"operation":"put","project_id":project_id,"data":data,
                 "memory_id":memory_id,"expected_version":expected_version}
        digest=hashlib.sha256(canonical(request)).digest()
        duplicate=self._existing_request(request_id,digest)
        if duplicate:return duplicate
        old=self.memories.get(memory_id) if memory_id else None
        if memory_id and (not old or old["project_id"]!=project_id or old["operation"]!="put"):
            raise KeyError("memory not found")
        if old and old["version"]!=expected_version:raise MemoryError(6)
        active=sum(r["operation"]=="put" for r in self.memories.values())
        if not old and active>=1000:raise MemoryError(5)
        now=time.time_ns()
        record={"schema":1,"operation":"put","memory_id":memory_id or str(uuid.uuid4()),
                "project_id":project_id,"version":old["version"]+1 if old else 1,
                "request_id":request_id,"created_at_ns":old["created_at_ns"] if old else now,
                "updated_at_ns":now,"data":data}
        return self._commit(record,request_id,digest)
    def forget(self, project_id,request_id,memory_id,expected_version):
        self._scope(project_id);identifier(request_id);identifier(memory_id)
        if type(expected_version) is not int or expected_version<1:raise ValueError("invalid expected_version")
        digest=hashlib.sha256(canonical({"operation":"delete","project_id":project_id,
                           "memory_id":memory_id,"expected_version":expected_version})).digest()
        duplicate=self._existing_request(request_id,digest)
        if duplicate:return duplicate
        old=self.memories.get(memory_id)
        if not old or old["project_id"]!=project_id or old["operation"]!="put":raise KeyError("memory not found")
        if old["version"]!=expected_version:raise MemoryError(6)
        now=time.time_ns()
        record={"schema":1,"operation":"delete","memory_id":memory_id,"project_id":project_id,
                "version":old["version"]+1,"request_id":request_id,
                "created_at_ns":old["created_at_ns"],"updated_at_ns":now,"data":None}
        return self._commit(record,request_id,digest)
    def get(self,project_id,memory_id):
        self._scope(project_id);identifier(memory_id)
        r=self.memories.get(memory_id)
        if not r or r["project_id"]!=project_id or r["operation"]!="put":raise KeyError("memory not found")
        return json.loads(canonical(r))
    def search(self,project_id,query,top_k=5,kind=None,conversation_id=None,tags=None):
        self._scope(project_id);text(query,"query",512)
        if type(top_k) is not int or not 1<=top_k<=5:raise ValueError("invalid top_k")
        if kind is not None and kind not in ("note","fact","decision","task"):raise ValueError("invalid kind")
        if conversation_id is not None:text(conversation_id,"conversation_id",128,True)
        if tags is not None:
            if type(tags) is not list or len(tags)>8:raise ValueError("invalid tags")
            for tag in tags:text(tag,"tag",64)
        q=normalized(query).strip();terms=sorted(set(q.split()))
        if not q:raise ValueError("query is whitespace")
        candidates=[]
        for r in self.memories.values():
            if r["operation"]!="put" or r["project_id"]!=project_id:continue
            d=r["data"]
            if kind is not None and d["kind"]!=kind:continue
            if conversation_id is not None and d["conversation_id"]!=conversation_id:continue
            if tags is not None and not set(tags)<=set(d["tags"]):continue
            title,body=self._search_text[r["memory_id"]]
            hits=sum(term in title or term in body for term in terms)
            if not hits:continue
            score=(int(q in title),int(q in body),hits,r["updated_at_ns"])
            candidates.append((score,r))
        candidates.sort(key=lambda pair:pair[1]["memory_id"])
        candidates.sort(key=lambda pair:pair[0],reverse=True)
        results=[];budget=16384
        for score,r in candidates[:top_k]:
            d=r["data"];snippet=d["text"][:512]
            size=len(snippet.encode())
            if size>budget:break
            budget-=size
            results.append({"memory_id":r["memory_id"],"version":r["version"],
                "title":d["title"],"snippet":snippet,"source":d["source"],
                "updated_at_ns":r["updated_at_ns"],
                "match_reason":{"title_phrase":bool(score[0]),"body_phrase":bool(score[1]),
                                "matched_terms":score[2]}})
        return {"hits":results,"count":len(results),"semantics":"keyword_substring"}
