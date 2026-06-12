"""
Git Module - Git repository ingestion subsystem.

Provides git credential management, repo cloning, branch
checkout, and code graph indexing.
"""

from git.api import app as git_app
from git.credentials import CredentialType, GitCredentialManager
from git.parser import CodeEntity, CodeParser
from git.pipeline import GitIngestionJob, GitIngestionPipeline
from git.repo import GitRepo, GitRepoManager, RepoSource

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
