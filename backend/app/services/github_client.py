import httpx
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Client for GitHub API integration
    """
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Amida-AI-Orchestrator/1.0"
        }
        
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def parse_pr_url(self, pr_url: str) -> tuple[str, str, int]:
        """
        Parse GitHub PR URL to extract owner, repo, and PR number
        Example: https://github.com/owner/repo/pull/123
        """
        pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, pr_url)
        
        if not match:
            raise ValueError(f"Invalid GitHub PR URL: {pr_url}")
        
        owner, repo, pr_number = match.groups()
        return owner, repo, int(pr_number)
    
    async def get_pr_data(self, pr_url: str) -> Dict[str, Any]:
        """
        Fetch PR data from GitHub API
        """
        try:
            owner, repo, pr_number = self.parse_pr_url(pr_url)
            
            async with httpx.AsyncClient() as client:
                # Get PR details
                pr_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers=self.headers
                )
                pr_response.raise_for_status()
                pr_data = pr_response.json()
                
                # Get PR diff
                diff_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                    headers={**self.headers, "Accept": "application/vnd.github.v3.diff"}
                )
                diff_response.raise_for_status()
                diff_content = diff_response.text
                
                # Get PR comments (optional)
                comments_response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
                    headers=self.headers
                )
                comments_response.raise_for_status()
                comments_data = comments_response.json()
                
                return {
                    "title": pr_data["title"],
                    "description": pr_data["body"] or "",
                    "author": pr_data["user"]["login"],
                    "state": pr_data["state"],
                    "created_at": pr_data["created_at"],
                    "updated_at": pr_data["updated_at"],
                    "diff": diff_content,
                    "comments": [
                        {
                            "author": comment["user"]["login"],
                            "body": comment["body"],
                            "created_at": comment["created_at"]
                        }
                        for comment in comments_data
                    ],
                    "commits_count": pr_data["commits"],
                    "additions": pr_data["additions"],
                    "deletions": pr_data["deletions"],
                    "changed_files": pr_data["changed_files"]
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                raise ValueError("PR not found or not accessible")
            elif e.response.status_code == 403:
                raise ValueError("Access denied - check GitHub token permissions")
            else:
                raise ValueError(f"GitHub API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching PR data: {str(e)}")
            raise
    
    async def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """
        Get repository information
        """
        try:
            # Parse repo URL
            pattern = r"https://github\.com/([^/]+)/([^/]+)/?$"
            match = re.match(pattern, repo_url)
            
            if not match:
                raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
            
            owner, repo = match.groups()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=self.headers
                )
                response.raise_for_status()
                repo_data = response.json()
                
                return {
                    "name": repo_data["name"],
                    "full_name": repo_data["full_name"],
                    "description": repo_data["description"],
                    "language": repo_data["language"],
                    "stars": repo_data["stargazers_count"],
                    "forks": repo_data["forks_count"],
                    "created_at": repo_data["created_at"],
                    "updated_at": repo_data["updated_at"]
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code}")
            raise ValueError("Repository not found or not accessible")
        except Exception as e:
            logger.error(f"Error fetching repository info: {str(e)}")
            raise
    
    async def get_file_content(self, repo_url: str, file_path: str, branch: str = "main") -> str:
        """
        Get content of a specific file from repository
        """
        try:
            # Parse repo URL
            pattern = r"https://github\.com/([^/]+)/([^/]+)/?$"
            match = re.match(pattern, repo_url)
            
            if not match:
                raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
            
            owner, repo = match.groups()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}",
                    headers=self.headers,
                    params={"ref": branch}
                )
                response.raise_for_status()
                file_data = response.json()
                
                # Decode base64 content
                import base64
                content = base64.b64decode(file_data["content"]).decode("utf-8")
                
                return content
                
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error: {e.response.status_code}")
            raise ValueError("File not found or not accessible")
        except Exception as e:
            logger.error(f"Error fetching file content: {str(e)}")
            raise