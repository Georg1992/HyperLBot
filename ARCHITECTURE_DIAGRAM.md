# HyperLBot Architecture Diagram
## Complete System Overview with Data Flows and Module Interactions

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                MAIN ENTRY POINT                                │
│                                    main.py                                     │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           TRADING ORCHESTRATOR                                 │
│                        core/bot/trading_orchestrator.py                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    COORDINATES 5 FOCUSED SERVICES                     │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │   Trading   │ │   Market    │ │  Dashboard  │ │   Session   │ │System│ │   │
│  │  │   Engine    │ │    Data     │ │  Service    │ │Orchestrator│ │Init. │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AI SYSTEM                                         │
│                        core/ai/unified_ai_system.py                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                       3-LAYER AI ARCHITECTURE                          │   │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           │   │
│  │  │ Initialization  │ │    Analysis     │ │    Execution    │           │   │
│  │  │     Layer       │ │     Layer       │ │     Layer       │           │   │
│  │  │                 │ │                 │ │                 │           │   │
│  │  │ • Data Sources  │ │ • Strategy      │ │ • Trade         │           │   │
│  │  │ • Components    │ │   Selection     │ │   Execution     │           │   │
│  │  │ • Readiness     │ │ • Predictions  │ │ • Monitoring    │           │   │
│  │  │ • Validation    │ │ • Reactions    │ │ • Risk Mgmt     │           │   │
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │ Hyperliquid │ │   Binance   │ │    Yahoo    │ │   Whale     │ │News │ │   │
│  │  │     API     │ │  WebSocket  │ │   Finance   │ │ Analytics  │ │RSS  │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        MARKET DATA MANAGER                                     │
│                        core/market_data_manager.py                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    CENTRALIZED DATA PROCESSING                         │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │ Volatility  │ │   Volume    │ │  Pressure   │ │     RSI     │ │S/R  │ │   │
│  │  │ Calculator  │ │ Calculator  │ │ Calculator  │ │ Calculator  │ │Calc │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │   Trend     │ │  Orderbook  │ │  Funding    │ │   Volume    │ │Cross│ │   │
│  │  │ Calculator  │ │  Analyzer   │ │   Rate      │ │  Profile    │ │Asset│ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SIGNAL SYSTEM                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │   Signal    │ │   Signal    │ │   Signal    │ │   Signal    │ │Signal│ │   │
│  │  │  Sources    │ │ Aggregator  │ │  Manager    │ │  Weights    │ │Types │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            ML SYSTEM                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │   Feature    │ │   Model     │ │ Prediction  │ │  Strategy   │ │Prob │ │   │
│  │  │ Engineering │ │  Training   │ │  Manager    │ │  Selector   │ │Eng. │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │ Continuous  │ │ Performance│ │ Prediction  │ │   Model     │ │ML   │ │   │
│  │  │  Learning   │ │  Monitor   │ │  Ensemble   │ │  Manager    │ │Models│ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION SYSTEM                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │   Trade     │ │  Position   │ │    Fee      │ │   Trade     │ │Risk │ │   │
│  │  │  Execution  │ │ Lifecycle   │ │  Manager    │ │  Quality    │ │Mgmt │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DASHBOARD                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │   Real-     │ │   Web       │ │   Data      │ │   Chart     │ │Web  │ │   │
│  │  │   time      │ │  Dashboard  │ │  Manager    │ │  Rendering  │ │Socket│ │   │
│  │  │  Updates    │ │   Service   │ │  (SimpleRTM)│ │   (HTML)    │ │ I/O │ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STRATEGIES                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────┐ │   │
│  │  │   Market    │ │   Strategy  │ │ Liquidation │ │   Pattern   │ │Range│ │   │
│  │  │ Conditions  │ │   Manager   │ │   Hunting   │ │ Recognition │ │Trading│ │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────┘ │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

## DATA FLOW ARCHITECTURE

### 1. DATA INGESTION FLOW
```
External APIs → Market Data Manager → Real-time Calculators → Signal Aggregator → AI System
```

### 2. AI DECISION FLOW
```
Initialization Layer → Analysis Layer → Execution Layer → Dashboard Updates
```

### 3. TRADING EXECUTION FLOW
```
AI Predictions → Execution Layer → Trade Management → Dashboard Display
```

### 4. DASHBOARD DATA FLOW
```
SimpleRTM (Data Hub) → WebSocket → Frontend → Real-time Updates
```

## MODULE INTERACTIONS

### Core Dependencies:
- **main.py** → **TradingOrchestrator** → **UnifiedAISystem**
- **UnifiedAISystem** → **InitializationLayer** + **AnalysisLayer** + **ExecutionLayer**
- **MarketDataManager** → **All Real-time Calculators**
- **SignalAggregator** → **All Signal Sources**
- **ML System** → **Feature Engineering** + **Model Training** + **Predictions**

### Service Dependencies:
- **TradingEngine** → **Execution System**
- **MarketDataService** → **MarketDataManager**
- **DashboardService** → **SimpleRTM**
- **SessionOrchestrator** → **Session Management**

## KEY ARCHITECTURAL PRINCIPLES

1. **Single Responsibility**: Each module has one clear purpose
2. **Lazy Imports**: Prevent circular dependencies
3. **Service Composition**: Orchestrator coordinates services
4. **Data Hub Pattern**: SimpleRTM as central data store
5. **Event-Driven**: WebSocket for real-time updates
6. **AI-Driven**: Multi-layer AI system for decisions
7. **Modular Design**: Clear separation of concerns
8. **Clean Architecture**: Dependencies point inward
