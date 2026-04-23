"""
Git Repo - Repository management for git operations.

Handles cloning, branch checkout, pulling, and file
reading with proper credential injection.
"""

import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from pydantic import BaseModel


class RepoSource(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    AZURE = "azure"
    GENERIC = "generic"


class RepoStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    CHECKING_OUT = "checking_out"
    PULLING = "pulling"
    READY = "ready"
    FAILED = "failed"


class GitFile(BaseModel):
    path: str
    content: str
    size: int
    language: Optional[str] = None


class GitCommit(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    files_changed: int


@dataclass
class GitRepo:
    repo_id: str
    url: str
    source: RepoSource
    local_path: str
    branch: str = "main"
    status: RepoStatus = RepoStatus.PENDING
    last_commit: Optional[str] = None
    file_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GitRepoManager:
    def __init__(
        self,
        base_path: Optional[str] = None,
        credential_manager: Optional[Any] = None,
    ):
        self.base_path = Path(base_path or tempfile.mkdtemp(prefix="git_repos_"))
        self.credential_manager = credential_manager
        self._repos: Dict[str, GitRepo] = {}

    def _detect_source(self, url: str) -> RepoSource:
        if "github.com" in url:
            return RepoSource.GITHUB
        elif "gitlab.com" in url:
            return RepoSource.GITLAB
        elif "bitbucket.org" in url:
            return RepoSource.BITBUCKET
        elif "azure.com" in url or "dev.azure.com" in url:
            return RepoSource.AZURE
        return RepoSource.GENERIC

    def _convert_ssh_to_https(self, url: str) -> str:
        match = re.match(r"git@([^:]+):(.+)\.git", url)
        if match:
            host, path = match.groups()
            if host == "github.com":
                return f"https://{host}/{path}.git"
        return url

    def _build_auth_url(self, url: str, credentials: Dict[str, Any]) -> str:
        if credentials.get("credential_type") == "none" or not credentials.get("token"):
            if url.startswith("git@"):
                return self._convert_ssh_to_https(url)
            return url

        cred_type = credentials.get("credential_type")
        token = credentials.get("token")
        username = credentials.get("username")

        if cred_type in ("https_token", "https_basic"):
            if username:
                return url.replace("https://", f"https://{username}:{token}@").replace(
                    "http://", f"http://{username}:{token}@"
                )
            else:
                return url.replace("https://", f"https://{token}@").replace(
                    "http://", f"http://{token}@"
                )

        return url

    def _ensure_ssh_key_permissions(self, key_path: str):
        key_file = Path(key_path)
        if key_file.exists():
            current_mode = key_file.stat().st_mode
            key_file.chmod(current_mode & 0o600)

    async def clone(
        self,
        url: str,
        branch: str = "main",
        deep_clone: bool = False,
    ) -> GitRepo:
        import time

        if url.startswith("-"):
            raise ValueError("Invalid URL: cannot start with '-' (argument injection prevention)")

        if branch.startswith("-"):
            raise ValueError("Invalid branch: cannot start with '-' (argument injection prevention)")

        repo_id = str(uuid.uuid4())[:8]
        source = self._detect_source(url)

        repo = GitRepo(
            repo_id=repo_id,
            url=url,
            source=source,
            local_path=str(self.base_path / repo_id),
            branch=branch,
            created_at=time.time(),
        )
        self._repos[repo_id] = repo

        repo.status = RepoStatus.CLONING

        credentials = {}
        if self.credential_manager:
            credentials = self.credential_manager.getcredential_for_url(url)

        auth_url = self._build_auth_url(url, credentials)

        cmd = ["git", "clone"]
        if not deep_clone:
            cmd.append("--depth=1")
        cmd.extend([auth_url, repo.local_path])

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            )
            if result.returncode != 0:
                repo.status = RepoStatus.FAILED
                repo.error = result.stderr
                return repo
        except Exception as e:
            repo.status = RepoStatus.FAILED
            repo.error = str(e)
            return repo

        repo.status = RepoStatus.CHECKING_OUT

        if branch and branch != "main":
            await self.checkout(repo_id, branch)

        if repo.status != RepoStatus.FAILED:
            repo.status = RepoStatus.READY
            repo.last_commit = await self.get_current_commit(repo_id)
            repo.file_count = len(await self.list_files(repo_id))

        repo.updated_at = time.time()
        return repo

    async def checkout(self, repo_id: str, branch: str) -> GitRepo:
        repo = self._repos.get(repo_id)
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")

        if branch.startswith("-"):
            raise ValueError("Invalid branch: cannot start with '-' (argument injection prevention)")

        repo.status = RepoStatus.CHECKING_OUT

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "checkout", branch],
                    cwd=repo.local_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            )
            if result.returncode != 0:
                repo.status = RepoStatus.FAILED
                repo.error = result.stderr
            else:
                repo.branch = branch
                repo.last_commit = await self.get_current_commit(repo_id)
        except Exception as e:
            repo.status = RepoStatus.FAILED
            repo.error = str(e)

        repo.updated_at = 0.0
        return repo

    async def pull(self, repo_id: str) -> GitRepo:
        import time

        repo = self._repos.get(repo_id)
        if not repo:
            raise ValueError(f"Repo {repo_id} not found")

        repo.status = RepoStatus.PULLING

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "pull", "origin", repo.branch],
                    cwd=repo.local_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            )
            if result.returncode != 0:
                repo.status = RepoStatus.FAILED
                repo.error = result.stderr
            else:
                repo.last_commit = await self.get_current_commit(repo_id)
                repo.updated_at = time.time()
        except Exception as e:
            repo.status = RepoStatus.FAILED
            repo.error = str(e)

        return repo

    async def get_current_commit(self, repo_id: str) -> Optional[str]:
        repo = self._repos.get(repo_id)
        if not repo:
            return None

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo.local_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error("Failed to get current commit for repo %s: %s", repo_id, e)
        return None

    async def list_branches(self, repo_id: str) -> List[str]:
        repo = self._repos.get(repo_id)
        if not repo:
            return []

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "branch", "-a"],
                    cwd=repo.local_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            )
            if result.returncode == 0:
                branches = []
                for line in result.stdout.split("\n"):
                    line = line.strip().replace("* ", "")
                    if line and not line.startswith("remotes/"):
                        branches.append(line)
                return branches
        except Exception as e:
            logger.error("Failed to list branches for repo %s: %s", repo_id, e)
        return []

    async def list_files(
        self,
        repo_id: str,
        extensions: Optional[List[str]] = None,
    ) -> List[str]:
        repo = self._repos.get(repo_id)
        if not repo:
            return []

        try:
            loop = asyncio.get_event_loop()
            cmd = ["git", "ls-files"]
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    cwd=repo.local_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            )
            if result.returncode != 0:
                return []

            files = result.stdout.strip().split("\n")

            if extensions:
                ext_set = set(e if e.startswith(".") else f".{e}" for e in extensions)
                files = [f for f in files if Path(f).suffix in ext_set]

            return files
        except Exception:
            return []

    async def read_file(self, repo_id: str, file_path: str) -> Optional[GitFile]:
        repo = self._repos.get(repo_id)
        if not repo:
            return None

        full_path = Path(repo.local_path) / file_path
        try:
            resolved = full_path.resolve()
        except (ValueError, OSError):
            return None
        repo_resolved = Path(repo.local_path).resolve()
        if not str(resolved).startswith(str(repo_resolved) + os.sep):
            return None
        if not full_path.exists():
            return None

        try:
            content = full_path.read_text()
            return GitFile(
                path=file_path,
                content=content,
                size=len(content),
                language=self._detect_language(file_path),
            )
        except Exception:
            return None

    async def read_files(
        self,
        repo_id: str,
        file_paths: List[str],
    ) -> Dict[str, GitFile]:
        files = {}
        for path in file_paths:
            file = await self.read_file(repo_id, path)
            if file:
                files[path] = file
        return files

    async def read_directory(
        self,
        repo_id: str,
        directory: str = "",
        max_files: int = 100,
    ) -> Dict[str, GitFile]:
        repo = self._repos.get(repo_id)
        if not repo:
            return {}

        dir_path = Path(repo.local_path) / directory
        if not dir_path.exists():
            return {}

        files = {}
        try:
            for item in dir_path.rglob("*"):
                if item.is_file() and len(files) < max_files:
                    rel_path = str(item.relative_to(dir_path))
                    try:
                        content = item.read_text()
                        files[rel_path] = GitFile(
                            path=rel_path,
                            content=content,
                            size=len(content),
                            language=self._detect_language(str(item)),
                        )
                    except Exception:
                        continue
        except Exception:
            pass

        return files

    async def get_commits(self, repo_id: str, limit: int = 10) -> List[GitCommit]:
        repo = self._repos.get(repo_id)
        if not repo:
            return []

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "log", f"-{limit}", "--pretty=format:%H%n%s%n%an%n%at"],
                    cwd=repo.local_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            )
            if result.returncode != 0:
                return []

            commits = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\n")
                if len(parts) >= 4:
                    commits.append(
                        GitCommit(
                            sha=parts[0],
                            message=parts[1],
                            author=parts[2],
                            date=parts[3],
                            files_changed=0,
                        )
                    )
            return commits
        except Exception as e:
            logger.error("Failed to get commits for repo %s: %s", repo_id, e)
            return []

    def _detect_language(self, file_path: str) -> Optional[str]:
        ext = Path(file_path).suffix.lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".scala": "scala",
            ".r": "r",
            ".sql": "sql",
            ".sh": "bash",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".json": "json",
            ".xml": "xml",
            ".md": "markdown",
        }
        return lang_map.get(ext)

    def get_repo(self, repo_id: str) -> Optional[GitRepo]:
        return self._repos.get(repo_id)

    def list_repos(self) -> List[Dict[str, Any]]:
        return [
            {
                "repo_id": r.repo_id,
                "url": r.url,
                "source": r.source.value,
                "branch": r.branch,
                "status": r.status.value,
                "file_count": r.file_count,
            }
            for r in self._repos.values()
        ]

    def delete_repo(self, repo_id: str) -> bool:
        repo = self._repos.pop(repo_id, None)
        if repo:
            shutil.rmtree(repo.local_path, ignore_errors=True)
            return True
        return False


_repo_manager: Optional[GitRepoManager] = None


def get_repo_manager() -> GitRepoManager:
    global _repo_manager
    if _repo_manager is None:
        from git.credentials import get_credential_manager

        _repo_manager = GitRepoManager(credential_manager=get_credential_manager())
    return _repo_manager
