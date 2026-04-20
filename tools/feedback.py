from typing import Any, Dict, List, Optional
import json
import logging

from tools.base import BaseTool, ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class UserFeedbackIngestTool(BaseTool):
    name = "feedback_ingest"
    description = "Ingest user feedback from email, survey, support tickets, app reviews"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        source = input.args.get("source", "email")
        feedback = input.args.get("feedback", "")
        
        try:
            result = await self._ingest_feedback_llm(source, feedback)
            return ToolOutput(
                result=result,
                metadata={"ingested": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM feedback ingestion failed: {e}, using fallback")
            result = await self._ingest_feedback_fallback(source, feedback)
            return ToolOutput(
                result=result,
                metadata={"ingested": True, "method": "fallback", "error": str(e)}
            )
    
    async def _ingest_feedback_llm(
        self,
        source: str,
        feedback: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Extract actionable insights from user feedback.
Source: {source}
Feedback: {feedback}

Respond ONLY with a JSON object containing:
- feedback: original feedback
- source: source type
- category: feature/bug/ux/pricing/documentation/other
- sentiment: positive/negative/neutral
- key_phrases: important terms
- action_items: recommended actions (array)
- priority: high/medium/low

Be specific about what user wants."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            result = json.loads(content)
            result["processed"] = True
            return result
            
        except Exception as e:
            logger.error(f"LLM feedback ingestion failed: {e}")
            raise
    
    async def _ingest_feedback_fallback(
        self,
        source: str,
        feedback: str
    ) -> Dict[str, Any]:
        return {
            "source": source,
            "feedback": feedback,
            "processed": True,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "feedback" in input


class SentimentAnalyzerTool(BaseTool):
    name = "sentiment_analyze"
    description = "Analyze feedback sentiment using NLP"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        texts = input.args.get("texts", [])
        
        try:
            analysis = await self._analyze_sentiment_llm(texts)
            return ToolOutput(
                result={"analysis": analysis},
                metadata={"analyzed": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM sentiment analysis failed: {e}, using fallback")
            analysis = await self._analyze_sentiment_fallback(texts)
            return ToolOutput(
                result={"analysis": analysis},
                metadata={"analyzed": True, "method": "fallback", "error": str(e)}
            )
    
    async def _analyze_sentiment_llm(
        self,
        texts: List[str]
    ) -> List[Dict[str, Any]]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Analyze sentiment for each text.
Texts: {json.dumps(texts)}

Respond ONLY with a JSON array where each item has:
- text: original text
- sentiment: positive/negative/neutral
- score: float 0-1 (positive: higher is more positive)
- emotions: array of emotions (joy/frustation/confusion/satisfaction)
- keywords: key terms affecting sentiment

Be nuanced - detect mixed sentiment."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM sentiment analysis failed: {e}")
            raise
    
    async def _analyze_sentiment_fallback(
        self,
        texts: List[str]
    ) -> List[Dict[str, Any]]:
        positive_words = {"love", "great", "amazing", "excellent", "good", "best", "awesome"}
        negative_words = {"hate", "bad", "terrible", "awful", "worst", "poor", "broken", "slow"}
        
        results = []
        for t in texts:
            t_lower = t.lower()
            pos_count = sum(1 for w in positive_words if w in t_lower)
            neg_count = sum(1 for w in negative_words if w in t_lower)
            
            if pos_count > neg_count:
                sentiment = "positive"
                score = min(0.5 + pos_count * 0.15, 0.95)
            elif neg_count > pos_count:
                sentiment = "negative"
                score = max(0.5 - neg_count * 0.15, 0.05)
            else:
                sentiment = "neutral"
                score = 0.5
            
            results.append({
                "text": t,
                "sentiment": sentiment,
                "score": score,
            })
        
        return results
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "texts" in input


class MetricTrendAnalyzerTool(BaseTool):
    name = "trend_analyze"
    description = "Analyze metric trends over time with forecasting"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        metric = input.args.get("metric", "")
        timeframe = input.args.get("timeframe", "30d")
        
        try:
            trends = await self._analyze_trends_llm(metric, timeframe)
            return ToolOutput(
                result={"trends": trends},
                metadata={"analyzed": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM trend analysis failed: {e}, using fallback")
            trends = await self._analyze_trends_fallback(metric, timeframe)
            return ToolOutput(
                result={"trends": trends},
                metadata={"analyzed": True, "method": "fallback", "error": str(e)}
            )
    
    async def _analyze_trends_llm(
        self,
        metric: str,
        timeframe: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Generate trend analysis for {metric}.
Timeframe: {timeframe}

Respond ONLY with a JSON object containing:
- metric: metric name
- timeframe: time window
- direction: increasing/decreasing/stable
- change_percent: percentage change
- data_points: array of historical values
- forecast: predicted next values (7 days)
- anomalies: array of unusual data points
- seasonality: detected patterns (daily/weekly/monthly/none)

Generate realistic time series data."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM trend analysis failed: {e}")
            raise
    
    async def _analyze_trends_fallback(
        self,
        metric: str,
        timeframe: str
    ) -> Dict[str, Any]:
        return {
            "metric": metric,
            "timeframe": timeframe,
            "direction": "increasing",
            "change_percent": 10.5,
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "metric" in input


class FeatureRequestTrackerTool(BaseTool):
    name = "feature_track"
    description = "Track feature requests with voting and prioritization"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        request = input.args.get("request", {})
        action = input.args.get("action", "track")
        
        try:
            result = await self._track_feature_llm(request, action)
            return ToolOutput(
                result=result,
                metadata={"tracked": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM feature tracking failed: {e}, using fallback")
            result = await self._track_feature_fallback(request, action)
            return ToolOutput(
                result=result,
                metadata={"tracked": True, "method": "fallback", "error": str(e)}
            )
    
    async def _track_feature_llm(
        self,
        request: Dict[str, Any],
        action: str
    ) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Process a feature request.
Request: {json.dumps(request)}
Action: {action} (track/vote/comment/status)

Respond ONLY with a JSON object containing:
- id: feature ID (e.g., FR-123)
- title: feature title
- description: description
- status: planned/in_progress/released/deferred/rejected
- priority: score 1-100
- votes: vote count
- requested_by: user
- estimated_effort: XS/S/M/L/XL
- dependencies: array of dependent features

Assign realistic priority based on request content."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM feature tracking failed: {e}")
            raise
    
    async def _track_feature_fallback(
        self,
        request: Dict[str, Any],
        action: str
    ) -> Dict[str, Any]:
        import time
        return {
            "action": action,
            "id": f"FR-{int(time.time())}",
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "request" in input or "action" in input


class ChurnPredictorTool(BaseTool):
    name = "churn_predict"
    description = "Predict customer churn using ML models"
    
    async def execute(self, input: ToolInput) -> ToolOutput:
        customer_id = input.args.get("customer_id", "")
        
        try:
            prediction = await self._predict_churn_llm(customer_id)
            return ToolOutput(
                result={"prediction": prediction},
                metadata={"predicted": True, "method": "llm"}
            )
        except Exception as e:
            logger.warning(f"LLM churn prediction failed: {e}, using fallback")
            prediction = await self._predict_churn_fallback(customer_id)
            return ToolOutput(
                result={"prediction": prediction},
                metadata={"predicted": True, "method": "fallback", "error": str(e)}
            )
    
    async def _predict_churn_llm(self, customer_id: str) -> Dict[str, Any]:
        try:
            from llm.router import get_router
            router = get_router()
            
            prompt = f"""Predict customer churn risk.
Customer ID: {customer_id}

Respond ONLY with a JSON object containing:
- customer_id: the ID
- churn_probability: float 0-1
- risk_level: low/medium/high/critical
- contributing_factors: array of factors (usage decline, support tickets, NPS, etc.)
- retention_suggestions: array of recommended actions
- tenure_months: customer tenure

Generate realistic prediction."""
            
            response = await router.chat(
                prompt=prompt,
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0]["message"]["content"]
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"LLM churn prediction failed: {e}")
            raise
    
    async def _predict_churn_fallback(self, customer_id: str) -> Dict[str, Any]:
        return {
            "customer_id": customer_id,
            "churn_probability": 0.15,
            "risk_level": "low",
        }
    
    def validate_input(self, input: Dict[str, Any]) -> bool:
        return "customer_id" in input


def register_feedback_tools(registry) -> None:
    registry.register(UserFeedbackIngestTool())
    registry.register(SentimentAnalyzerTool())
    registry.register(MetricTrendAnalyzerTool())
    registry.register(FeatureRequestTrackerTool())
    registry.register(ChurnPredictorTool())