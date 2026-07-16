"""
Git Module - Git repository ingestion subsystem.

Provides git credential management, repo cloning, branch
checkout, and code graph indexing.
"""

from git.credentials import GitCredentialManager, CredentialType
from git.repo import GitRepoManager, GitRepo, RepoSource
from git.parser import CodeParser, CodeEntity
from git.pipeline import GitIngestionPipeline, GitIngestionJob
from git.api import app as git_app


__all__ = [
    "GitCredentialManager",
    "CredentialType",
    "GitRepoManager",
    "GitRepo",
    "RepoSource",
    "CodeParser",
    "CodeEntity",
    "GitIngestionPipeline",
    "GitIngestionJob",
    "git_app",
]
