#!/usr/bin/env python3
"""
AI Module
========
Multi-layer AI system for trading decisions and execution.
"""

# Initialization layer removed - SystemInitializer handles all initialization
from core.ai.analysis_layer import global_analysis_layer, AnalysisLayer
from core.ai.execution_layer import global_execution_layer, ExecutionLayer
from core.ai.unified_ai_system import global_unified_ai_system, UnifiedAISystem

__all__ = [
    'global_analysis_layer', 
    'global_execution_layer',
    'global_unified_ai_system',
    'AnalysisLayer',
    'ExecutionLayer',
    'UnifiedAISystem'
]
