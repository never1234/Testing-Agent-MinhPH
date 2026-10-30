"""Bug tracker / task board clients: Trello, Jira, Mantis and a sheet-based tracker.

Every client exposes:
  me()                         -> {"id", "name"}
  open_issues()                -> [(key, title, url)]          (duplicate check)
  create_issue(bug, title, body, files) -> (key, url)
  list_tasks(queues)           -> [task dict]                  (QC work queue, see normalize below)
  get_task(key)                -> task dict + "comments", "attachments"
  move(key, state_name)        -> str  (what happened)
  comment(key, text)
  attach(key, files)
  claim(key)                   -> assign/add me
  download(att, dest_dir)      -> Path | None
  validate(workflow)           -> [warning strings]
  finish()                     -> flush (sheet tracker)

Task dict: key, url, title, desc, queue, status, labels[], members[], due (ISO or ""), created, updated,
           priority_raw[]  (labels / priority names used for priority mapping)
"""
from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import KIT_ROOT, die, env, today, warn

PLATFORM_NAMES = {"android": "Android", "ios": "iOS", "web": "Web"}
TIMEOUT = 30


def _rel(p: Path) -> str:
    try:
        return str(Path(p).relative_to(KIT_ROOT))
    except ValueError:
        return str(p)


def _ci(a: str, b: str) -> bool:
    return (a or "").strip().lower() == (b or "").strip().lower()


def steps_text(bug: dict) -> str:
    steps = bug.get("steps") or []
    if isinstance(steps, str):
        return steps
    return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))


# ======================================================================
class Trello:
    kind = "trello"
    API = "https://api.trello.com/1"

    def __init__(self, cfg: dict, dry: bool = False):
        self.cfg = cfg
        self.dry = dry
        self.auth = {"key": env("TRELLO_KEY"), "token": env("TRELLO_TOKEN")}
        self.board = cfg.get("board_id") or die("bug_tracker.trello.board_id missing in profile.yaml")
        self._lists = None
        self._labels = None
        self._me = None

    # -- http
    def _req(self, method, path, **kw):
        params = {**self.auth, **kw.pop("params", {})}
        r = requests.request(method, self.API + path, params=params, timeout=kw.pop("timeout", TIMEOUT), **kw)
        if not r.ok:
            die(f"Trello {method} {path}: {r.status_code} {r.text[:300]}")
        return r.json() if r.text else {}

    def _get(self, path, **params):
        return self._req("GET", path, params=params)

    # -- lookups
    def lists(self) -> dict:
        if self._lists is None:
            self._lists = {lst["id"]: lst["name"] for lst in self._get(f"/boards/{self.board}/lists", fields="name")}
        return self._lists

    def list_id(self, name: str) -> str | None:
        return next((i for i, n in self.lists().items() if _ci(n, name)), None)

    def labels(self) -> dict:
        if self._labels is None:
            self._labels = {lb["id"]: lb.get("name") or lb.get("color", "") for lb in self._get(f"/boards/{self.board}/labels")}
        return self._labels

    def me(self) -> dict:
        if self._me is None:
            m = self._get("/members/me", fields="id,username,fullName")
            self._me = {"id": m["id"], "name": m.get("fullName") or m.get("username")}
        return self._me

    def _card(self, key: str) -> dict:
        k = str(key).strip()
        if k.startswith("http"):
            k = k.rstrip("/").split("/c/")[-1].split("/")[0]
            return self._get(f"/cards/{k}")
        k = k.lstrip("#")
        if k.isdigit():
            return self._get(f"/boards/{self.board}/cards/{k}")
        return self._get(f"/cards/{k}")

    def _norm(self, c: dict, queue: str = "") -> dict:
        names = [lb.get("name") or lb.get("color", "") for lb in c.get("labels") or []]
        created = datetime.fromtimestamp(int(c["id"][:8], 16), tz=timezone.utc).isoformat()
        return {
            "key": f"#{c['idShort']}", "url": c.get("shortUrl", ""), "title": c.get("name", ""),
            "desc": c.get("desc", ""), "queue": queue, "status": self.lists().get(c.get("idList"), ""),
            "labels": names, "members": c.get("idMembers") or [], "due": c.get("due") or "",
            "due_complete": bool(c.get("dueComplete")), "created": created,
            "updated": c.get("dateLastActivity", ""), "priority_raw": names, "_id": c["id"],
        }

    # -- duplicate check / create
    def open_issues(self):
        cards = self._get(f"/boards/{self.board}/cards/open", fields="name,shortUrl,idShort")
        return [(f"#{c['idShort']}", c["name"], c["shortUrl"]) for c in cards]

    def create_issue(self, bug, title, body, files):
        lst = self.list_id(self.cfg.get("list_name", "To Do")) or die(
            f"Trello list '{self.cfg.get('list_name')}' not found. Lists: {list(self.lists().values())}")
        names = list(self.cfg.get("labels") or [])
        sev = (self.cfg.get("severity_labels") or {}).get(bug.get("severity", ""))
        if sev:
            names.append(sev)
        params = {"idList": lst, "name": title, "desc": body[:16000], "pos": "top"}
        ids = [i for i, n in self.labels().items() if any(_ci(n, x) for x in names)]
        if ids:
            params["idLabels"] = ",".join(ids)
        card = self._req("POST", "/cards", params=params)
        self.attach(card["id"], files)
        return f"#{card['idShort']}", card["shortUrl"]

    # -- tasks
    def list_tasks(self, queues: dict) -> list:
        cards = self._get(f"/boards/{self.board}/cards/open",
                          fields="name,desc,idList,labels,idMembers,due,dueComplete,shortUrl,idShort,dateLastActivity")
        out, seen = [], set()
        for qname, q in queues.items():
            want_lists = [self.list_id(n) for n in q.get("lists") or []]
            want_lists = [x for x in want_lists if x]
            for c in cards:
                if c["id"] in seen or (want_lists and c["idList"] not in want_lists):
                    continue
                labels = [lb.get("name", "") for lb in c.get("labels") or []]
                if q.get("labels_any") and not any(_ci(a, b) for a in labels for b in q["labels_any"]):
                    continue
                if not want_lists and not q.get("labels_any"):
                    continue
                seen.add(c["id"])
                out.append(self._norm(c, qname))
        return out

    def get_task(self, key):
        c = self._card(key)
        c.setdefault("labels", [])
        t = self._norm(c)
        acts = self._get(f"/cards/{c['id']}/actions", filter="commentCard", limit=50)
        t["comments"] = [{"author": (a.get("memberCreator") or {}).get("fullName", ""), "date": a.get("date", ""),
                          "text": (a.get("data") or {}).get("text", "")} for a in reversed(acts)]
        atts = self._get(f"/cards/{c['id']}/attachments", fields="name,url,mimeType,isUpload,bytes")
        t["attachments"] = [{"name": a.get("name"), "url": a.get("url"), "mime": a.get("mimeType") or "",
                             "upload": a.get("isUpload", False)} for a in atts]
        return t

    def _id(self, key):
        return key if re.fullmatch(r"[0-9a-f]{24}", str(key)) else self._card(key)["id"]

    def move(self, key, state):
        lst = self.list_id(state)
        if not lst:
            die(f"Trello list '{state}' not found. Lists: {list(self.lists().values())}")
        self._req("PUT", f"/cards/{self._id(key)}", params={"idList": lst, "pos": "top"})
        return f"moved to list '{state}'"

    def comment(self, key, text):
        self._req("POST", f"/cards/{self._id(key)}/actions/comments", params={"text": text[:16000]})

    def attach(self, key, files):
        cid = self._id(key) if files else None
        for fp in files:
            with open(fp, "rb") as fh:
                r = requests.post(f"{self.API}/cards/{cid}/attachments", params=self.auth,
                                  files={"file": (Path(fp).name, fh)}, timeout=120)
            if not r.ok:
                warn(f"Attach {Path(fp).name} failed: {r.status_code}")

    def claim(self, key):
        cid, me = self._id(key), self.me()["id"]
        c = self._get(f"/cards/{cid}", fields="idMembers")
        if me not in (c.get("idMembers") or []):
            self._req("POST", f"/cards/{cid}/idMembers", params={"value": me})
        return "added me as member"

    def download(self, att, dest: Path):
        if not att.get("upload"):
            return None
        hdr = {"Authorization": f'OAuth oauth_consumer_key="{self.auth["key"]}", oauth_token="{self.auth["token"]}"'}
        r = requests.get(att["url"], headers=hdr, timeout=120)
        if not r.ok:
            warn(f"Download {att['name']} failed: {r.status_code}")
            return None
        dest.mkdir(parents=True, exist_ok=True)
        p = dest / re.sub(r"[^\w.\-]", "_", att["name"] or "attachment")
        p.write_bytes(r.content)
        return p

    def validate(self, wf):
        names = list(self.lists().values())
        warns = []
        for q, d in (wf.get("queues") or {}).items():
            for n in d.get("lists") or []:
                if not any(_ci(n, x) for x in names):
                    warns.append(f"queue {q}: list '{n}' not on board")
        for s, n in (wf.get("states") or {}).items():
            if n and not any(_ci(n, x) for x in names):
                warns.append(f"state {s}: list '{n}' not on board")
        if warns:
            warns.append(f"board lists are: {names}")
        return warns

    def finish(self):
        pass


# ======================================================================
def _adf_text(node) -> str:
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    sep = "\n" if node.get("type") in ("paragraph", "heading", "listItem", "codeBlock", "doc") else ""
    return sep.join(_adf_text(c) for c in node.get("content") or []) + ("\n" if sep and node.get("type") != "doc" else "")


class Jira:
    kind = "jira"

    def __init__(self, cfg: dict, dry: bool = False):
        self.cfg = cfg
        self.base = env("JIRA_BASE_URL").rstrip("/")
        self.cloud = cfg.get("deployment", "cloud") == "cloud"
        self.s = requests.Session()
        self.s.headers["Accept"] = "application/json"
        if self.cloud:
            self.s.auth = (env("JIRA_EMAIL"), env("JIRA_API_TOKEN"))
        else:
            self.s.headers["Authorization"] = f"Bearer {env('JIRA_PAT')}"
        self.pkey = cfg.get("project_key") or die("bug_tracker.jira.project_key missing in profile.yaml")
        self._me = None

    def _req(self, method, path, **kw):
        r = self.s.request(method, self.base + path, timeout=kw.pop("timeout", TIMEOUT), **kw)
        if not r.ok:
            die(f"Jira {method} {path}: {r.status_code} {r.text[:400]}")
        return r.json() if r.text else {}

    def me(self):
        if self._me is None:
            m = self._req("GET", "/rest/api/2/myself")
            self._me = {"id": m.get("accountId") or m.get("name"), "name": m.get("displayName", "")}
        return self._me

    def _search(self, jql, fields, limit=200):
        if self.cloud:
            data = self._req("GET", "/rest/api/3/search/jql", params={"jql": jql, "fields": fields, "maxResults": limit})
        else:
            data = self._req("GET", "/rest/api/2/search", params={"jql": jql, "fields": fields, "maxResults": limit})
        return data.get("issues", [])

    def _norm(self, i, queue=""):
        f = i.get("fields") or {}
        prio = (f.get("priority") or {}).get("name", "")
        desc = f.get("description") or ""
        if isinstance(desc, dict):
            desc = _adf_text(desc).strip()
        assignee = f.get("assignee") or {}
        return {
            "key": i["key"], "url": f"{self.base}/browse/{i['key']}", "title": f.get("summary", ""), "desc": desc,
            "queue": queue, "status": (f.get("status") or {}).get("name", ""), "labels": f.get("labels") or [],
            "members": [x for x in [assignee.get("accountId") or assignee.get("name")] if x],
            "due": f.get("duedate") or "", "due_complete": False, "created": f.get("created", ""),
            "updated": f.get("updated", ""), "priority_raw": [prio] + (f.get("labels") or []),
            "issuetype": (f.get("issuetype") or {}).get("name", ""),
        }

    def open_issues(self):
        jql = self.cfg.get("dedup_jql") or (f'project = "{self.pkey}" AND issuetype = "{self.cfg.get("issue_type", "Bug")}" '
                                            f'AND statusCategory != Done ORDER BY created DESC')
        return [(i["key"], i["fields"]["summary"], f"{self.base}/browse/{i['key']}") for i in self._search(jql, "summary")]

    def create_issue(self, bug, title, body, files):
        fields = {"project": {"key": self.pkey}, "summary": title[:250], "description": body,
                  "issuetype": {"name": self.cfg.get("issue_type", "Bug")}}
        prio = (self.cfg.get("severity_to_priority") or {}).get(bug.get("severity", ""))
        if prio:
            fields["priority"] = {"name": prio}
        if self.cfg.get("labels"):
            fields["labels"] = list(self.cfg["labels"])
        if self.cfg.get("components"):
            fields["components"] = [{"name": c} for c in self.cfg["components"]]
        fields.update(self.cfg.get("extra_fields") or {})
        key = self._req("POST", "/rest/api/2/issue", json={"fields": fields})["key"]
        self.attach(key, files)
        if bug.get("parent_task") and self.cfg.get("link_type"):
            self._req("POST", "/rest/api/2/issueLink", json={"type": {"name": self.cfg["link_type"]},
                      "inwardIssue": {"key": key}, "outwardIssue": {"key": bug["parent_task"]}})
        return key, f"{self.base}/browse/{key}"

    def list_tasks(self, queues):
        fields = "summary,status,priority,labels,duedate,created,updated,assignee,description,issuetype"
        out, seen = [], set()
        for qname, q in queues.items():
            jql = q.get("jql")
            if not jql:
                continue
            for i in self._search(jql, fields):
                if i["key"] not in seen:
                    seen.add(i["key"])
                    out.append(self._norm(i, qname))
        return out

    def get_task(self, key):
        i = self._req("GET", f"/rest/api/2/issue/{key}",
                      params={"fields": "summary,status,priority,labels,duedate,created,updated,assignee,"
                                        "description,issuetype,comment,attachment,fixVersions"})
        t = self._norm(i)
        f = i["fields"]
        t["fix_versions"] = [v.get("name") for v in f.get("fixVersions") or []]
        t["comments"] = [{"author": (c.get("author") or {}).get("displayName", ""), "date": c.get("created", ""),
                          "text": c.get("body", "") if isinstance(c.get("body"), str) else _adf_text(c.get("body"))}
                         for c in (f.get("comment") or {}).get("comments", [])]
        t["attachments"] = [{"name": a.get("filename"), "url": a.get("content"), "mime": a.get("mimeType", ""),
                             "upload": True} for a in f.get("attachment") or []]
        return t

    def move(self, key, state):
        trs = self._req("GET", f"/rest/api/2/issue/{key}/transitions").get("transitions", [])
        tr = next((t for t in trs if _ci(t["name"], state) or _ci((t.get("to") or {}).get("name", ""), state)), None)
        if not tr:
            die(f"Jira {key}: no transition to '{state}'. Available: "
                f"{[(t['name'], (t.get('to') or {}).get('name')) for t in trs]}")
        self._req("POST", f"/rest/api/2/issue/{key}/transitions", json={"transition": {"id": tr["id"]}})
        return f"transitioned via '{tr['name']}'"

    def comment(self, key, text):
        self._req("POST", f"/rest/api/2/issue/{key}/comment", json={"body": text})

    def attach(self, key, files):
        for fp in files:
            with open(fp, "rb") as fh:
                r = self.s.post(f"{self.base}/rest/api/2/issue/{key}/attachments",
                                headers={"X-Atlassian-Token": "no-check"}, files={"file": (Path(fp).name, fh)}, timeout=120)
            if not r.ok:
                warn(f"Attach {Path(fp).name} failed: {r.status_code}")

    def claim(self, key):
        me = self.me()["id"]
        body = {"accountId": me} if self.cloud else {"name": me}
        self._req("PUT", f"/rest/api/2/issue/{key}/assignee", json=body)
        return "assigned to me"

    def download(self, att, dest: Path):
        r = self.s.get(att["url"], timeout=120)
        if not r.ok:
            warn(f"Download {att['name']} failed: {r.status_code}")
            return None
        dest.mkdir(parents=True, exist_ok=True)
        p = dest / re.sub(r"[^\w.\-]", "_", att["name"] or "attachment")
        p.write_bytes(r.content)
        return p

    def validate(self, wf):
        warns = []
        for q, d in (wf.get("queues") or {}).items():
            if not d.get("jql"):
                warns.append(f"queue {q}: jql missing (Jira queues are defined by JQL)")
        return warns

    def finish(self):
        pass


# ======================================================================
class Mantis:
    kind = "mantis"

    def __init__(self, cfg: dict, dry: bool = False):
        self.cfg = cfg
        self.base = env("MANTIS_BASE_URL").rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": env("MANTIS_TOKEN"), "Accept": "application/json"})
        self.pid = cfg.get("project_id") or die("bug_tracker.mantis.project_id missing in profile.yaml")
        self._me = None

    def _req(self, method, path, **kw):
        r = self.s.request(method, f"{self.base}/api/rest{path}", timeout=kw.pop("timeout", TIMEOUT), **kw)
        if not r.ok:
            die(f"Mantis {method} {path}: {r.status_code} {r.text[:400]}")
        return r.json() if r.text else {}

    def me(self):
        if self._me is None:
            m = self._req("GET", "/users/me")
            self._me = {"id": m.get("id"), "name": m.get("real_name") or m.get("name", "")}
        return self._me

    def _all(self, pages=10):
        out = []
        for page in range(1, pages + 1):
            issues = self._req("GET", "/issues", params={"project_id": self.pid, "page_size": 100, "page": page}).get("issues", [])
            out += issues
            if len(issues) < 100:
                break
        return out

    def _norm(self, i, queue=""):
        iid = i["id"]
        handler = (i.get("handler") or {}).get("id")
        return {
            "key": f"#{iid}", "url": f"{self.base}/view.php?id={iid}", "title": i.get("summary", ""),
            "desc": "\n\n".join(x for x in [i.get("description", ""), i.get("steps_to_reproduce", "")] if x),
            "queue": queue, "status": (i.get("status") or {}).get("name", ""),
            "labels": [t.get("name", "") for t in i.get("tags") or []],
            "members": [handler] if handler else [], "due": i.get("due_date") or "", "due_complete": False,
            "created": i.get("created_at", ""), "updated": i.get("updated_at", ""),
            "priority_raw": [(i.get("priority") or {}).get("name", ""), (i.get("severity") or {}).get("name", "")],
            "fixed_in_version": (i.get("fixed_in_version") or {}).get("name", ""),
        }

    def open_issues(self):
        return [(f"#{i['id']}", i.get("summary", ""), f"{self.base}/view.php?id={i['id']}") for i in self._all(5)
                if (i.get("status") or {}).get("name") not in ("resolved", "closed")]

    def create_issue(self, bug, title, body, files):
        sev_map = self.cfg.get("severity_map") or {"critical": "crash", "major": "major", "minor": "minor", "trivial": "trivial"}
        payload = {"summary": title[:128], "description": body, "steps_to_reproduce": steps_text(bug),
                   "category": {"name": self.cfg.get("category", "General")}, "project": {"id": int(self.pid)}}
        if bug.get("severity") in sev_map:
            payload["severity"] = {"name": sev_map[bug["severity"]]}
        if files:
            payload["files"] = [{"name": Path(fp).name, "content": base64.b64encode(Path(fp).read_bytes()).decode()} for fp in files]
        iid = self._req("POST", "/issues", json=payload, timeout=120)["issue"]["id"]
        return f"#{iid}", f"{self.base}/view.php?id={iid}"

    def list_tasks(self, queues):
        issues = self._all()
        out, seen = [], set()
        for qname, q in queues.items():
            sts = q.get("statuses") or []
            for i in issues:
                st = (i.get("status") or {}).get("name", "")
                if i["id"] in seen or not any(_ci(st, s) for s in sts):
                    continue
                seen.add(i["id"])
                out.append(self._norm(i, qname))
        return out

    def get_task(self, key):
        iid = str(key).lstrip("#")
        i = self._req("GET", f"/issues/{iid}")["issues"][0]
        t = self._norm(i)
        t["comments"] = [{"author": (n.get("reporter") or {}).get("name", ""), "date": n.get("created_at", ""),
                          "text": n.get("text", "")} for n in i.get("notes") or []]
        t["attachments"] = [{"name": a.get("filename"), "url": f"/issues/{iid}/files/{a.get('id')}", "mime": a.get("content_type", ""),
                             "upload": True} for a in i.get("attachments") or []]
        return t

    def move(self, key, state):
        iid = str(key).lstrip("#")
        body = {"status": {"name": state}}
        if state in ("resolved", "closed"):
            body["resolution"] = {"name": "fixed"}
        if state in ("feedback", "assigned", "new"):
            body.pop("resolution", None)
        self._req("PATCH", f"/issues/{iid}", json=body)
        return f"status -> {state}"

    def comment(self, key, text):
        self._req("POST", f"/issues/{str(key).lstrip('#')}/notes", json={"text": text, "view_state": {"name": "public"}})

    def attach(self, key, files):
        if files:
            self._req("POST", f"/issues/{str(key).lstrip('#')}/files", timeout=120,
                      json={"files": [{"name": Path(f).name, "content": base64.b64encode(Path(f).read_bytes()).decode()} for f in files]})

    def claim(self, key):
        self._req("PATCH", f"/issues/{str(key).lstrip('#')}", json={"handler": {"id": self.me()["id"]}})
        return "handler set to me"

    def download(self, att, dest: Path):
        data = self._req("GET", att["url"]).get("files", [])
        if not data:
            return None
        dest.mkdir(parents=True, exist_ok=True)
        p = dest / re.sub(r"[^\w.\-]", "_", att["name"] or "attachment")
        p.write_bytes(base64.b64decode(data[0].get("content", "")))
        return p

    def validate(self, wf):
        return [f"queue {q}: statuses missing" for q, d in (wf.get("queues") or {}).items() if not d.get("statuses")]

    def finish(self):
        pass


# ======================================================================
class SheetTracker:
    """Bugs tab inside the test-case book (or another book). Status column drives the QC workflow."""
    kind = "sheet"
    HEADER = ["Bug ID", "Title", "Module", "Platform", "Severity", "Priority", "TC ID", "Steps", "Expected",
              "Actual", "Evidence", "Status", "Reporter", "Date", "Parent Task", "QC Note"]

    def __init__(self, cfg: dict, prof: dict, dry: bool = False):
        from .sheets import open_book, open_testcase_book
        self.book = open_book(cfg["source"], cfg.get("excel_path"), cfg.get("gsheet_id")) if cfg.get("source") \
            else open_testcase_book(prof)
        self.name = cfg.get("sheet_name", "Bugs")
        self.prefix = cfg.get("id_prefix", "BUG_")
        self.dry = dry
        self.values = self.book.values(self.name) if self.name in self.book.sheet_names() else []
        if not self.values and not dry:
            self.book.add_sheet(self.name, self.HEADER)
            self.values = [list(self.HEADER)]
        self.header = [h.strip() for h in (self.values[0] if self.values else self.HEADER)]
        self.next_row = max(len(self.values), 1) + 1
        nums = [int(m.group(1)) for row in self.values[1:] if row and
                (m := re.match(rf"^{re.escape(self.prefix)}(\d+)$", row[0].strip()))]
        self.next_num = max(nums, default=0) + 1

    def _col(self, name, create=False):
        for i, h in enumerate(self.header):
            if _ci(h, name):
                return i + 1
        if create:
            self.header.append(name)
            c = len(self.header)
            self.book.write(self.name, [(1, c, name)])
            return c
        return None

    def _rowdict(self, row):
        return {h: (row[i].strip() if i < len(row) else "") for i, h in enumerate(self.header)}

    def _find(self, key):
        for r, row in enumerate(self.values[1:], start=2):
            if row and _ci(row[0], key):
                return r, self._rowdict(row)
        die(f"{key} not found in tab '{self.name}'")

    def me(self):
        return {"id": "me", "name": "Claude QA"}

    def open_issues(self):
        st = self._col("Status")
        closed = {"closed", "verified", "done", "rejected"}
        return [(row[0], row[1], "") for row in self.values[1:] if len(row) > 1 and row[0]
                and not (st and len(row) >= st and row[st - 1].strip().lower() in closed)]

    def create_issue(self, bug, title, body, files):
        bid = f"{self.prefix}{self.next_num:03d}"
        vals = {"Bug ID": bid, "Title": title, "Module": bug.get("module", ""),
                "Platform": PLATFORM_NAMES.get(bug.get("platform", ""), bug.get("platform", "")),
                "Severity": bug.get("severity", ""), "TC ID": ", ".join(bug.get("tc_ids") or []),
                "Steps": steps_text(bug), "Expected": bug.get("expected", ""), "Actual": bug.get("actual", ""),
                "Evidence": "\n".join(_rel(f) for f in files), "Status": "New", "Reporter": "Claude QA",
                "Date": today(), "Parent Task": bug.get("parent_task", "")}
        ups = [(self.next_row, c, v) for k, v in vals.items() if v and (c := self._col(k, create=True))]
        self.book.write(self.name, ups)
        self.values.append([vals.get(h, "") for h in self.header])
        self.next_row += 1
        self.next_num += 1
        return bid, f"{self.name}!A{self.next_row - 1}"

    def list_tasks(self, queues):
        out, seen = [], set()
        for qname, q in queues.items():
            sts = q.get("statuses") or []
            for row in self.values[1:]:
                if not row or not row[0].strip():
                    continue
                d = self._rowdict(row)
                if d["Bug ID"] in seen or not any(_ci(d.get("Status", ""), s) for s in sts):
                    continue
                seen.add(d["Bug ID"])
                out.append({"key": d["Bug ID"], "url": "", "title": d.get("Title", ""),
                            "desc": "\n".join(f"{k}: {d.get(k, '')}" for k in ("Module", "Platform", "Severity", "TC ID",
                                                                              "Steps", "Expected", "Actual") if d.get(k)),
                            "queue": qname, "status": d.get("Status", ""),
                            "labels": [x.strip() for x in re.split(r"[,/]", d.get("Platform", "")) if x.strip()],
                            "members": [],
                            "due": "", "due_complete": False, "created": d.get("Date", ""), "updated": "",
                            "priority_raw": [d.get("Priority", ""), d.get("Severity", "")]})
        return out

    def get_task(self, key):
        _, d = self._find(key)
        t = next((x for x in self.list_tasks({"_": {"statuses": [d.get("Status", "")]}}) if x["key"] == d["Bug ID"]), None)
        t["queue"] = ""
        t["comments"] = [{"author": "", "date": "", "text": d.get("QC Note", "")}] if d.get("QC Note") else []
        t["attachments"] = [{"name": e, "url": e, "mime": "", "upload": False} for e in d.get("Evidence", "").splitlines() if e]
        return t

    def move(self, key, state):
        r, _ = self._find(key)
        self.book.write(self.name, [(r, self._col("Status", create=True), state)])
        return f"Status -> {state}"

    def comment(self, key, text):
        r, d = self._find(key)
        old = d.get("QC Note", "")
        line = f"[{today()}] {text}"
        self.book.write(self.name, [(r, self._col("QC Note", create=True), f"{old}\n{line}" if old else line)])

    def attach(self, key, files):
        if files:
            r, d = self._find(key)
            ev = d.get("Evidence", "")
            add = "\n".join(_rel(f) for f in files)
            self.book.write(self.name, [(r, self._col("Evidence", create=True), f"{ev}\n{add}" if ev else add)])

    def claim(self, key):
        return "sheet tracker: nothing to assign"

    def download(self, att, dest):
        return None

    def validate(self, wf):
        return [f"queue {q}: statuses missing" for q, d in (wf.get("queues") or {}).items() if not d.get("statuses")]

    def finish(self):
        self.book.save()


# ======================================================================
def make_client(prof: dict, dry: bool = False):
    cfg = prof.get("bug_tracker") or {}
    kind = (cfg.get("type") or "none").lower()
    sub = cfg.get(kind) or {}
    if kind == "trello":
        return Trello(sub, dry), cfg
    if kind == "jira":
        return Jira(sub, dry), cfg
    if kind == "mantis":
        return Mantis(sub, dry), cfg
    if kind in ("sheet", "excel", "gsheet"):
        return SheetTracker(cfg.get("sheet") or {}, prof, dry), cfg
    die("bug_tracker.type is 'none' - set sheet|trello|jira|mantis in profile.yaml")
