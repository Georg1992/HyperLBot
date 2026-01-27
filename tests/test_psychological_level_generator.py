#!/usr/bin/env python3
"""
Unit tests for PsychologicalLevelGenerator
"""

import pytest
from core.calculations.psychological_level_generator import PsychologicalLevelGenerator


class TestPsychologicalLevelGenerator:
    """Test psychological level generation"""
    
    def test_price_below_10k(self):
        """Test spacing for price < $10k"""
        current_price = 8500.0
        levels = PsychologicalLevelGenerator.generate_levels(current_price)
        
        # Should have minor=100, major=1000 spacing
        assert len(levels) > 0
        
        # Check spacing
        prices = [l["price_level"] for l in levels]
        for price in prices:
            # Should be divisible by 100 (minor) or 1000 (major)
            assert price % 100 < 0.01 or price % 1000 < 0.01
    
    def test_price_10k_to_50k(self):
        """Test spacing for price $10k-$50k"""
        current_price = 35000.0
        levels = PsychologicalLevelGenerator.generate_levels(current_price)
        
        # Should have minor=500, major=5000 spacing
        assert len(levels) > 0
        
        prices = [l["price_level"] for l in levels]
        for price in prices:
            # Should be divisible by 500 (minor) or 5000 (major)
            assert price % 500 < 0.01 or price % 5000 < 0.01
    
    def test_price_above_50k(self):
        """Test spacing for price > $50k (e.g., near $100k)"""
        current_price = 95000.0
        levels = PsychologicalLevelGenerator.generate_levels(current_price)
        
        # Should have minor=1000, major=10000 spacing
        assert len(levels) > 0
        
        prices = [l["price_level"] for l in levels]
        for price in prices:
            # Should be divisible by 1000 (minor) or 10000 (major)
            assert price % 1000 < 0.01 or price % 10000 < 0.01
        
        # Should include $100k (major level)
        assert any(abs(l["price_level"] - 100000.0) < 0.01 for l in levels)
    
    def test_level_format(self):
        """Test that levels conform to S/R level format"""
        current_price = 95000.0
        levels = PsychologicalLevelGenerator.generate_levels(current_price)
        
        assert len(levels) > 0
        
        for level in levels:
            # Required fields
            assert "price_level" in level
            assert "type" in level
            assert level["type"] in ["support", "resistance"]
            assert "strength_score" in level
            assert "power" in level
            assert "status" in level
            assert level["status"] == "active"
            assert "source" in level
            assert level["source"] == "psych"
            
            # Value ranges
            assert 0.0 <= level["strength_score"] <= 100.0
            assert 0.0 <= level["power"] <= 100.0
            assert level["price_level"] > 0
    
    def test_strength_calculation(self):
        """Test strength calculation based on divisibility"""
        # Test major level (divisible by major * 2)
        strength_100k = PsychologicalLevelGenerator._calculate_strength(100000.0, 1000.0, 10000.0)
        assert strength_100k == 1.0  # Base 0.4 + 0.2 (minor) + 0.2 (major) + 0.2 (major*2) = 1.0
        
        # Test major level (divisible by major)
        strength_90k = PsychologicalLevelGenerator._calculate_strength(90000.0, 1000.0, 10000.0)
        assert 0.6 <= strength_90k <= 1.0  # Base 0.4 + bonuses
        
        # Test minor level (divisible by minor only)
        strength_91k = PsychologicalLevelGenerator._calculate_strength(91000.0, 1000.0, 10000.0)
        assert 0.4 <= strength_91k < 0.8  # Base 0.4 + minor bonus
    
    def test_support_resistance_classification(self):
        """Test that levels below price are support, above are resistance"""
        current_price = 95000.0
        levels = PsychologicalLevelGenerator.generate_levels(current_price)
        
        for level in levels:
            if level["price_level"] < current_price:
                assert level["type"] == "support"
            elif level["price_level"] > current_price:
                assert level["type"] == "resistance"
    
    def test_range_5_percent(self):
        """Test that levels are generated ±5% around current price"""
        current_price = 100000.0
        levels = PsychologicalLevelGenerator.generate_levels(current_price)
        
        min_price = current_price * 0.95  # 95k
        max_price = current_price * 1.05  # 105k
        
        for level in levels:
            assert min_price <= level["price_level"] <= max_price
    
    def test_deterministic(self):
        """Test that generation is deterministic"""
        current_price = 95000.0
        levels1 = PsychologicalLevelGenerator.generate_levels(current_price)
        levels2 = PsychologicalLevelGenerator.generate_levels(current_price)
        
        assert len(levels1) == len(levels2)
        prices1 = sorted([l["price_level"] for l in levels1])
        prices2 = sorted([l["price_level"] for l in levels2])
        assert prices1 == prices2
    
    def test_example_near_100k(self):
        """Example output near $100k BTC"""
        current_price = 98000.0
        levels = PsychologicalLevelGenerator.generate_levels(current_price)
        
        # Should include levels like 95k, 96k, 97k, 98k, 99k, 100k, 101k, 102k, 103k
        prices = [l["price_level"] for l in levels]
        
        # Check for major level $100k
        assert any(abs(p - 100000.0) < 0.01 for p in prices)
        
        # Check for minor levels
        assert any(abs(p - 95000.0) < 0.01 for p in prices)
        assert any(abs(p - 100000.0) < 0.01 for p in prices)
        
        # Verify format
        for level in levels:
            print(f"Level: ${level['price_level']:.2f}, Type: {level['type']}, Power: {level['power']:.1f}, Source: {level['source']}")
        
        assert len(levels) > 0
