# Separation of Concerns Analysis

## Overall Architecture Assessment

### ✅ **GOOD: Well-Separated Areas**

1. **Data Providers** (`core/calculations/*_data_provider.py`)
   - ✅ Properly separated: Handle data fetching only
   - ✅ Use dependency injection for services
   - ✅ No business logic, just data access

2. **Calculators** (`core/calculations/*_calculator.py`)
   - ✅ Generally well-structured with dependency injection
   - ✅ Use data providers for data access (SRDataProvider, PressureDataProvider, etc.)
   - ✅ Focus on calculations, not data fetching

3. **Services** (`core/services/`)
   - ✅ MarketDataService: Coordinates analysis modules (good)
   - ✅ DashboardService: Handles presentation data (good)
   - ✅ SessionOrchestrator: Coordinates main loop (good)

4. **Analysis Modules** (`core/analysis/`)
   - ✅ Separate from calculations
   - ✅ Real-time analysis separated from historical

---

## ⚠️ **ISSUES: Separation of Concerns Violations**

### 1. **Prediction Engine Doing Calculations**

**Location:** `core/execution/prediction_engine.py`

**Issues:**
- `_calculate_dynamic_entry_price()` (lines 1348-1580)
  - **Problem:** Complex calculation logic (200+ lines) in prediction engine
  - **Should be:** In a dedicated `EntryPriceCalculator` module
  - **Impact:** Mixes business logic (prediction) with calculation logic (entry price math)

- `_calculate_stop_and_target()` (lines 1943-2213)
  - **Problem:** Stop loss and take profit calculations in prediction engine
  - **Partially Fixed:** S/R level selection delegated to `SupportResistanceCalculator.select_stop_loss_level()`
  - **Remaining Issue:** Risk management calculations (ATR-based stops, R:R calculations) still in prediction engine
  - **Should be:** In a dedicated `RiskManager` or `StopLossCalculator` module

**Recommendation:**
```python
# Create: core/calculations/entry_price_calculator.py
class EntryPriceCalculator:
    @staticmethod
    def calculate_dynamic_entry_price(
        level_price: float,
        current_price: float,
        direction: str,
        setup_type: str,
        level_data: Dict[str, Any],
        unified_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Optional[float]:
        # Move all entry price calculation logic here
        pass

# Create: core/calculations/risk_manager.py
class RiskManager:
    @staticmethod
    def calculate_stop_loss(
        entry_price: float,
        direction: str,
        sr_level: Optional[Dict],
        atr_5m: float,
        config: Dict[str, Any]
    ) -> float:
        # Move stop loss calculation logic here
        pass
    
    @staticmethod
    def calculate_take_profit(
        entry_price: float,
        stop_loss: float,
        direction: str,
        config: Dict[str, Any]
    ) -> float:
        # Move take profit calculation logic here
        pass
```

---

### 2. **Service Doing Calculations**

**Location:** `core/services/market_data_service.py`

**Issue:**
- `recalculate_rsi_baseline()` (line 280)
  - **Problem:** Service method that directly calls calculator method
  - **Current:** Service coordinates, which is correct
  - **Status:** ✅ Actually OK - service is just coordinating, not calculating

**Status:** ✅ No issue here - service is properly coordinating

---

### 3. **Calculator Accessing Historical Service Directly**

**Location:** `core/calculations/support_resistance_calculator.py`

**Issue:**
- Lines 438-440: Direct access to `historical_service` for MTF candles
  ```python
  candles_data['15m'] = historical_service.get_historical_candles("BTC", "15m", ...)
  candles_data['1h'] = historical_service.get_historical_candles("BTC", "1h", ...)
  candles_data['1d'] = historical_service.get_historical_candles("BTC", "1d", ...)
  ```
  - **Problem:** Calculator bypasses data provider for some timeframes
  - **Should be:** All data access through `SRDataProvider`
  - **Impact:** Inconsistent data access pattern

**Recommendation:**
- Move all historical service calls to `SRDataProvider`
- Calculator should only use `self._data_provider` for all data access

---

### 4. **Prediction Engine Data Extraction**

**Location:** `core/execution/prediction_engine.py`

**Issue:**
- `_get_atr_pct()` (line 52)
  - **Problem:** Data extraction logic in prediction engine
  - **Status:** ✅ Actually OK - this is just data access, not calculation
  - **Note:** Could be a utility method, but acceptable in prediction engine

**Status:** ✅ Acceptable - simple data extraction

---

## 📊 **Summary of Issues**

### **Critical Issues (Should Fix):**

1. **Entry Price Calculation in Prediction Engine**
   - **File:** `core/execution/prediction_engine.py`
   - **Method:** `_calculate_dynamic_entry_price()`
   - **Action:** Move to `core/calculations/entry_price_calculator.py`

2. **Stop Loss/Take Profit Calculation in Prediction Engine**
   - **File:** `core/execution/prediction_engine.py`
   - **Method:** `_calculate_stop_and_target()`
   - **Action:** Move risk management calculations to `core/calculations/risk_manager.py`

3. **Calculator Bypassing Data Provider**
   - **File:** `core/calculations/support_resistance_calculator.py`
   - **Lines:** 438-440
   - **Action:** Move all data access to `SRDataProvider`

---

## 🎯 **Recommended Refactoring Priority**

### **Priority 1: High Impact**
1. Extract entry price calculation to `EntryPriceCalculator`
2. Extract stop loss/take profit to `RiskManager`

### **Priority 2: Medium Impact**
3. Fix calculator data access to use data provider consistently

### **Priority 3: Low Impact (Already Acceptable)**
4. Keep simple data extraction in prediction engine (acceptable)

---

## ✅ **What's Working Well**

1. **Data Provider Pattern:** Calculators use data providers (SRDataProvider, PressureDataProvider, etc.)
2. **Dependency Injection:** Good use of DI in calculators
3. **Service Layer:** Services properly coordinate, don't calculate
4. **Analysis Modules:** Separated from calculations
5. **S/R Level Selection:** Recently refactored to use `SupportResistanceCalculator.select_stop_loss_level()`

---

## 📝 **Architecture Principles Applied**

✅ **Single Responsibility Principle:** Mostly followed
- Data providers: Data access only
- Calculators: Calculations only
- Services: Coordination only
- ⚠️ Prediction engine: Mixes prediction logic with calculations

✅ **Dependency Inversion:** Good use of dependency injection
- Calculators inject data providers
- Services inject calculators

✅ **Separation of Concerns:** Generally good
- ⚠️ Some calculation logic in prediction engine (should be in calculators)
