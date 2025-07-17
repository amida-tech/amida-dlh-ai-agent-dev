import asyncio
from typing import Optional, Dict, Any
import openai
from openai import AsyncAzureOpenAI
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AzureAIClient:
    """
    Client for Azure OpenAI (Grok 3) integration
    """
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION
        )
        self.model_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        
    async def get_completion(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> Any:
        """
        Get completion from Azure OpenAI
        """
        try:
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message
            
        except Exception as e:
            logger.error(f"Error getting AI completion: {str(e)}")
            raise
    
    async def get_completion_with_usage(
        self, 
        prompt: str, 
        system_message: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> tuple[Any, Dict[str, int]]:
        """
        Get completion with token usage information
        """
        try:
            messages = []
            
            if system_message:
                messages.append({"role": "system", "content": system_message})
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
            
            return response.choices[0].message, usage
            
        except Exception as e:
            logger.error(f"Error getting AI completion: {str(e)}")
            raise
    
    async def analyze_document(self, document_content: str, analysis_type: str = "general") -> Dict[str, Any]:
        """
        Analyze document content using AI
        """
        system_message = f"""You are an expert document analyst. 
        Please provide a {analysis_type} analysis of the given document.
        Focus on key insights, important information, and actionable items."""
        
        prompt = f"""
        Please analyze this document:
        
        {document_content}
        
        Provide a comprehensive analysis including:
        1. Summary of main points
        2. Key findings or insights
        3. Recommendations or action items
        4. Any concerns or issues identified
        """
        
        message, usage = await self.get_completion_with_usage(
            prompt=prompt,
            system_message=system_message
        )
        
        return {
            "analysis": message.content,
            "tokens_used": usage["total_tokens"],
            "model_used": self.model_name
        }
    
    async def review_code(self, code_content: str, context: str = "") -> Dict[str, Any]:
        """
        Review code using AI
        """
        system_message = """You are an expert code reviewer. 
        Analyze the code for quality, security, performance, and best practices.
        Provide specific, actionable feedback."""
        
        prompt = f"""
        Please review this code:
        
        Context: {context}
        
        Code:
        {code_content}
        
        Please provide:
        1. Overall code quality assessment
        2. Security vulnerabilities or concerns
        3. Performance considerations
        4. Best practice violations
        5. Specific suggestions for improvement
        6. Positive aspects of the code
        """
        
        message, usage = await self.get_completion_with_usage(
            prompt=prompt,
            system_message=system_message
        )
        
        return {
            "review": message.content,
            "tokens_used": usage["total_tokens"],
            "model_used": self.model_name
        }
    
    async def generate_content(
        self, 
        content_type: str, 
        topic: str, 
        requirements: str = "",
        target_audience: str = "general"
    ) -> Dict[str, Any]:
        """
        Generate content (reports, papers, etc.) using AI
        """
        system_message = f"""You are an expert writer specializing in {content_type} creation.
        Write clear, well-structured, and informative content tailored to the {target_audience} audience."""
        
        prompt = f"""
        Please write a {content_type} on the following topic:
        
        Topic: {topic}
        Target Audience: {target_audience}
        Requirements: {requirements}
        
        Please ensure the content is:
        1. Well-structured with clear sections
        2. Informative and accurate
        3. Appropriate for the target audience
        4. Professional in tone
        5. Actionable where relevant
        """
        
        message, usage = await self.get_completion_with_usage(
            prompt=prompt,
            system_message=system_message,
            max_tokens=4000  # Longer for content generation
        )
        
        return {
            "content": message.content,
            "tokens_used": usage["total_tokens"],
            "model_used": self.model_name
        }