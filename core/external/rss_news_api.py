#!/usr/bin/env python3
"""
RSS News Sentiment API Client
=============================
High-quality RSS-based crypto news sentiment analysis
Fetches from multiple reputable sources and analyzes sentiment using VADER
"""

import feedparser
import requests
import time
import re
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from loguru import logger
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import hashlib


class RSSNewsAPI:
    """
    High-quality RSS-based crypto news sentiment fetcher
    
    Features:
    - Multiple reputable crypto news sources
    - VADER sentiment analysis (proven for financial news)
    - BTC-specific filtering
    - Duplicate detection
    - Quality scoring
    - Real-time updates
    """
    
    def __init__(self):
        # Use centralized cache system
        from core.services.centralized_cache import get_global_centralized_cache
        self._cache = get_global_centralized_cache()
        
        self.news_limit = 50  # Max articles to analyze per update
        
        # Initialize VADER sentiment analyzer (optimized for financial news)
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # High-quality crypto news sources
        # Note: Some feeds may be temporarily disabled if they consistently fail
        self.disabled_feeds = set()  # Track feeds that consistently fail
        self.rss_feeds = {
            'coindesk': {
                'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml',
                'weight': 1.0,  # Highest weight - most reputable
                'btc_keywords': ['bitcoin', 'btc', 'cryptocurrency', 'crypto']
            },
            'cointelegraph': {
                'url': 'https://cointelegraph.com/rss',
                'weight': 0.9,
                'btc_keywords': ['bitcoin', 'btc', 'cryptocurrency', 'crypto']
            },
            'bitcoin_magazine': {
                'url': 'https://bitcoinmagazine.com/feed',
                'weight': 0.8,
                'btc_keywords': ['bitcoin', 'btc']
            },
            'decrypt': {
                'url': 'https://decrypt.co/feed',
                'weight': 0.7,
                'btc_keywords': ['bitcoin', 'btc', 'cryptocurrency', 'crypto']
            },
            'the_block': {
                'url': 'https://www.theblock.co/rss.xml',
                'weight': 0.8,
                'btc_keywords': ['bitcoin', 'btc', 'cryptocurrency', 'crypto']
            }
        }
        
        # Enhanced financial sentiment keywords
        self.bullish_keywords = [
            'bullish', 'surge', 'rally', 'moon', 'pump', 'breakout', 'uptrend',
            'positive', 'gains', 'rise', 'increase', 'growth', 'adoption',
            'institutional', 'etf', 'approval', 'partnership', 'upgrade',
            'hodl', 'diamond hands', 'buy the dip', 'accumulation',
            'institutional adoption', 'mainstream', 'regulation clarity'
        ]
        
        self.bearish_keywords = [
            'bearish', 'crash', 'dump', 'decline', 'fall', 'downtrend', 'correction',
            'negative', 'loss', 'drop', 'decrease', 'sell-off', 'fear', 'panic',
            'regulation', 'ban', 'hack', 'security', 'risk', 'warning',
            'fud', 'paper hands', 'sell-off', 'liquidation', 'margin call'
        ]
        
        # Request headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        logger.info("📰 RSS News Fetcher initialized - High-quality sentiment analysis")
    
    def get_news_sentiment(self) -> Dict[str, Any]:
        """
        Get comprehensive news sentiment analysis from RSS feeds
        
        Returns:
            Dict containing sentiment analysis, impact assessment, and trading signals
        """
        try:
            cache_key = "news_sentiment"
            current_time = time.time()
            
            # Check cache using centralized system
            cached_data = self._cache.get(cache_key)
            if cached_data:
                logger.debug("📰 Using cached news sentiment data")
                return cached_data
            
            # Fetch real RSS news articles
            logger.info("📰 Fetching real news from RSS feeds...")
            all_articles = self._fetch_all_news()
            
            if not all_articles:
                logger.warning("⚠️ No articles fetched from RSS feeds")
                raise ValueError("Real news sentiment data not available - NO FALLBACKS: No articles fetched")
            
            # Analyze sentiment from real articles
            sentiment_analysis = self._analyze_sentiment(all_articles)
            
            # Create comprehensive result with all required fields
            sentiment_data = sentiment_analysis['sentiment']
            result = {
                'sentiment': {
                    'classification': sentiment_data['classification'],
                    'score': sentiment_data['score'],
                    'confidence': sentiment_analysis['confidence'],
                    'bullish_count': sentiment_data.get('bullish_count', 0),
                    'bearish_count': sentiment_data.get('bearish_count', 0),
                    'neutral_count': sentiment_data.get('neutral_count', 0),
                    'total_news': len(all_articles)  # Total articles analyzed
                },
                'impact': sentiment_analysis['impact'],
                'trading_signals': sentiment_analysis['trading_signal'],  # Fixed: plural key name
                'confidence': sentiment_analysis['confidence'],
                'articles': all_articles[:10],  # Include top 10 articles for reference
                'total_articles': len(all_articles),
                'sources': list(set([article['source'] for article in all_articles])),
                'timestamp': current_time,
                'data_source': 'rss_feeds',
                'cache_duration': 900  # 15 minutes cache
            }
            
            # Cache result using centralized system
            # Use CentralizedCache TTL instead of hardcoded value
            self._cache.set(cache_key, result)
            
            logger.info(f"📰 News sentiment: {sentiment_analysis['sentiment']['classification']} "
                       f"({sentiment_analysis['confidence']:.1%} confidence, {len(all_articles)} articles)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ News sentiment analysis failed: {e}")
            raise ValueError(f"News sentiment analysis failed - NO FALLBACKS: {e}")
    
    def _fetch_all_news(self) -> List[Dict[str, Any]]:
        """Fetch news from all RSS feeds"""
        all_articles = []
        successful_feeds = 0
        
        for source_name, source_config in self.rss_feeds.items():
            # Skip disabled feeds
            if source_name in self.disabled_feeds:
                logger.debug(f"⏭️ Skipping disabled feed: {source_name}")
                continue
                
            try:
                articles = self._fetch_rss_feed(source_name, source_config)
                if articles:
                    all_articles.extend(articles)
                    successful_feeds += 1
                    logger.info(f"✅ Fetched {len(articles)} BTC articles from {source_name}")
                else:
                    logger.debug(f"📰 No BTC articles from {source_name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch from {source_name}: {e}")
                # Don't disable feeds immediately - they might be temporarily down
                continue
        
        logger.info(f"📊 RSS Fetch Summary: {successful_feeds}/{len(self.rss_feeds)} feeds successful, {len(all_articles)} total articles")
        
        # Remove duplicates and sort by date (using timestamp for sorting)
        unique_articles = self._remove_duplicates(all_articles)
        sorted_articles = sorted(unique_articles, key=lambda x: x['published_timestamp'], reverse=True)
        
        return sorted_articles[:self.news_limit]
    
    def _fetch_rss_feed(self, source_name: str, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed"""
        try:
            response = requests.get(
                source_config['url'], 
                headers=self.headers, 
                timeout=10,
                verify=True  # Enable SSL verification
            )
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            articles = []
            
            for entry in feed.entries:
                # Extract article data
                published_date = self._parse_date(entry.get('published', ''))
                article = {
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', ''),
                    'link': entry.get('link', ''),
                    'published': published_date.isoformat() if published_date else None,  # Convert to ISO string for JSON
                    'published_timestamp': published_date.timestamp() if published_date else time.time(),  # For sorting
                    'source': source_name,
                    'weight': source_config['weight'],
                    'btc_keywords': source_config['btc_keywords']
                }
                
                # Filter for BTC-related content
                if self._is_btc_related(article):
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            # Log as warning instead of error to reduce noise
            logger.warning(f"⚠️ RSS fetch failed for {source_name}: {e}")
            return []
    
    def _is_btc_related(self, article: Dict[str, Any]) -> bool:
        """Check if article is Bitcoin-related"""
        text = f"{article['title']} {article['summary']}".lower()
        
        # Check for BTC keywords
        for keyword in article['btc_keywords']:
            if keyword.lower() in text:
                return True
        
        # Additional BTC-specific patterns
        btc_patterns = [
            r'\bbtc\b', r'bitcoin', r'cryptocurrency', r'crypto',
            r'digital currency', r'virtual currency'
        ]
        
        for pattern in btc_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats from RSS feeds"""
        try:
            # Try common RSS date formats
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Fallback to current time
            return datetime.now()
            
        except Exception:
            return datetime.now()
    
    def _remove_duplicates(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on title similarity"""
        unique_articles = []
        seen_hashes = set()
        
        for article in articles:
            # Create hash from title and first 100 chars of summary
            content = f"{article['title']}{article['summary'][:100]}"
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_articles.append(article)
        
        return unique_articles
    
    def _analyze_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment using VADER and keyword analysis"""
        if not articles:
            return self._create_neutral_sentiment()
        
        # Analyze each article
        article_sentiments = []
        weighted_scores = []
        
        for article in articles:
            # Combine title and summary for analysis
            text = f"{article['title']} {article['summary']}"
            
            # VADER sentiment analysis
            vader_scores = self.sentiment_analyzer.polarity_scores(text)
            
            # Keyword-based sentiment
            keyword_sentiment = self._analyze_keywords(text)
            
            # Combine VADER and keyword analysis
            combined_sentiment = self._combine_sentiment_scores(vader_scores, keyword_sentiment)
            
            # Apply source weight
            weighted_score = combined_sentiment * article['weight']
            
            article_sentiments.append({
                'sentiment': combined_sentiment,
                'vader_scores': vader_scores,
                'keyword_sentiment': keyword_sentiment,
                'weight': article['weight'],
                'title': article['title'][:100]  # For debugging
            })
            
            weighted_scores.append(weighted_score)
        
        # Calculate overall sentiment
        if weighted_scores:
            avg_sentiment = sum(weighted_scores) / len(weighted_scores)
        else:
            avg_sentiment = 0.0
        
        # Determine classification
        if avg_sentiment > 0.1:
            classification = 'bullish'
        elif avg_sentiment < -0.1:
            classification = 'bearish'
        else:
            classification = 'neutral'
        
        # Calculate confidence based on sentiment strength and article count
        confidence = min(abs(avg_sentiment) * 2, 1.0)  # Scale to 0-1
        confidence = max(confidence, 0.1)  # Minimum 10% confidence
        
        # Determine impact level
        impact_level = self._determine_impact_level(avg_sentiment, len(articles), confidence)
        
        # Count high impact articles (strong sentiment + high confidence)
        high_impact_count = len([s for s in article_sentiments if abs(s['sentiment']) > 0.3])
        
        # Generate trading signal
        trading_signal = self._generate_trading_signal(classification, confidence, impact_level)
        
        return {
            'sentiment': {
                'classification': classification,
                'score': avg_sentiment,
                'bullish_count': len([s for s in weighted_scores if s > 0.1]),
                'bearish_count': len([s for s in weighted_scores if s < -0.1]),
                'neutral_count': len([s for s in weighted_scores if -0.1 <= s <= 0.1])
            },
            'impact': {
                'impact_level': impact_level,
                'strength': abs(avg_sentiment),
                'article_count': len(articles),
                'high_impact_count': high_impact_count  # Required (NO FALLBACKS)
            },
            'trading_signal': trading_signal,
            'confidence': confidence,
            'articles': article_sentiments[:5]  # Top 5 for debugging
        }
    
    def _analyze_keywords(self, text: str) -> float:
        """Analyze sentiment based on financial keywords"""
        text_lower = text.lower()
        
        bullish_count = sum(1 for keyword in self.bullish_keywords if keyword in text_lower)
        bearish_count = sum(1 for keyword in self.bearish_keywords if keyword in text_lower)
        
        if bullish_count + bearish_count == 0:
            return 0.0
        
        # Normalize to -1 to 1 range
        sentiment = (bullish_count - bearish_count) / (bullish_count + bearish_count)
        return sentiment * 0.5  # Scale down keyword influence
    
    def _combine_sentiment_scores(self, vader_scores: Dict[str, float], keyword_sentiment: float) -> float:
        """Combine VADER and keyword sentiment scores"""
        # VADER compound score is already normalized to -1 to 1
        vader_score = vader_scores['compound']
        
        # Weighted combination: 70% VADER, 30% keywords
        combined = (vader_score * 0.7) + (keyword_sentiment * 0.3)
        
        # Ensure result is in -1 to 1 range
        return max(-1.0, min(1.0, combined))
    
    def _determine_impact_level(self, sentiment_score: float, article_count: int, confidence: float) -> str:
        """Determine the impact level of news sentiment"""
        # High impact: strong sentiment + many articles + high confidence
        if abs(sentiment_score) > 0.3 and article_count > 10 and confidence > 0.7:
            return 'high'
        
        # Medium impact: moderate sentiment + decent articles + good confidence
        elif abs(sentiment_score) > 0.15 and article_count > 5 and confidence > 0.5:
            return 'medium'
        
        # Low impact: weak sentiment or few articles
        else:
            return 'low'
    
    def _generate_trading_signal(self, classification: str, confidence: float, impact_level: str) -> Dict[str, Any]:
        """Generate trading signal based on news sentiment"""
        if impact_level == 'high' and confidence > 0.7:
            if classification == 'bullish':
                return {
                    'signal': 'BUY',
                    'strength': 'strong',
                    'reasoning': f'Strong bullish news sentiment ({confidence:.1%} confidence)'
                }
            elif classification == 'bearish':
                return {
                    'signal': 'SELL',
                    'strength': 'strong',
                    'reasoning': f'Strong bearish news sentiment ({confidence:.1%} confidence)'
                }
        
        elif impact_level == 'medium' and confidence > 0.5:
            if classification == 'bullish':
                return {
                    'signal': 'BUY',
                    'strength': 'moderate',
                    'reasoning': f'Moderate bullish news sentiment ({confidence:.1%} confidence)'
                }
            elif classification == 'bearish':
                return {
                    'signal': 'SELL',
                    'strength': 'moderate',
                    'reasoning': f'Moderate bearish news sentiment ({confidence:.1%} confidence)'
                }
        
        return {
            'signal': 'NEUTRAL',
            'strength': 'weak',
            'reasoning': f'Neutral news sentiment ({confidence:.1%} confidence)'
        }
    
    def _create_neutral_sentiment(self) -> Dict[str, Any]:
        """Create neutral sentiment when no articles are available"""
        return {
            'sentiment': {
                'classification': 'neutral',
                'score': 0.0,
                'bullish_count': 0,
                'bearish_count': 0,
                'neutral_count': 0
            },
            'impact': {
                'impact_level': 'low',
                'strength': 0.0,
                'article_count': 0
            },
            'trading_signal': {
                'signal': 'NEUTRAL',
                'strength': 'weak',
                'reasoning': 'No recent news available'
            },
            'confidence': 0.1,
            'articles': []
        }
    
    # _create_fallback_sentiment method removed - NO FALLBACKS policy
    
    def test_connection(self) -> Dict[str, Any]:
        """Test RSS feed connections"""
        results = {}
        
        for source_name, source_config in self.rss_feeds.items():
            try:
                response = requests.get(source_config['url'], headers=self.headers, timeout=5)
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    article_count = len(feed.entries) if feed.entries else 0
                    results[source_name] = {
                        'status': 'success',
                        'articles_found': article_count,
                        'url': source_config['url']
                    }
                else:
                    results[source_name] = {
                        'status': 'error',
                        'error': f'HTTP {response.status_code}',
                        'url': source_config['url']
                    }
            except Exception as e:
                results[source_name] = {
                    'status': 'error',
                    'error': str(e),
                    'url': source_config['url']
                }
        
        return results


# Global instance
# Singleton pattern implementation
_global_rss_news_api = None

def get_global_rss_news_api() -> RSSNewsAPI:
    """Get the global RSSNewsAPI singleton instance"""
    global _global_rss_news_api
    if _global_rss_news_api is None:
        _global_rss_news_api = RSSNewsAPI()
    return _global_rss_news_api

# Backward compatibility
rss_news_api = get_global_rss_news_api()
