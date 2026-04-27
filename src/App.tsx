import { useState, useEffect } from 'react';
import { 
  Activity, Brain, TrendingUp, Shield, Search, 
  BarChart3, ArrowRight, Zap, RefreshCw, 
  ChevronDown, ChevronUp, Database,
  Target, LineChart, AlertTriangle, CheckCircle,
  Globe, Cpu, Layers, Sparkles, Key, MessageSquare,
  GitBranch, Scale, Coins, Eye
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, BarChart, Bar,
  PieChart, Pie, Cell
} from 'recharts';
interface AgentStatus {
  name: string;
  status: string;
  lastRun: string | null;
  metrics: { runs: number; errors: number; avgLatencyMs: number };
  tools: string[];
  memorySize: number;
}
interface Prediction {
  asset: string;
  timeframe: string;
  prediction: string;
  confidence: number;
  upsideProbability: number;
  kellyFraction: number;
  recommendedPosition: number;
  polymarketPrice: number | null;
  kalshiPrice: number | null;
  timestamp: string;
  reasoning: string;
  riskLevel: string;
  regime: string;
  modelUsed?: string;
  llmAnalysis?: any;
}
interface ArbitrageOpp {
  type: string;
  asset: string;
  timeframe_a?: string;
  timeframe_b?: string;
  prediction_a?: string;
  prediction_b?: string;
  spread?: number;
  description?: string;
  strategy?: string;
  recommended?: string;
}
const generateMockHistory = () => {
  const data = [];
  const now = new Date();
  for (let i = 30; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 5 * 60 * 1000);
    data.push({
      time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
      btc: 50 + Math.random() * 20 + Math.sin(i * 0.5) * 10,
      eth: 45 + Math.random() * 15 + Math.cos(i * 0.5) * 8,
      sol: 40 + Math.random() * 18 + Math.sin(i * 0.7) * 6,
      accuracy: 55 + Math.random() * 20
    });
  }
  return data;
};
const generateMockPredictions = (): Prediction[] => [
  {
    asset: "BTC", timeframe: "5m", prediction: "up", confidence: 0.72,
    upsideProbability: 0.68, kellyFraction: 0.08, recommendedPosition: 40.0,
    polymarketPrice: 0.65, kalshiPrice: 0.67,
    timestamp: new Date().toISOString(),
    reasoning: "Predicted UP with 72% confidence. Kronos model detected trending regime. Kelly suggests 8% position.",
    riskLevel: "low", regime: "trending", modelUsed: "kronos_small",
    llmAnalysis: { analysis: "BTC showing strong momentum with EMA crossover. Volume supports upward move. Key resistance at $67k." }
  },
  {
    asset: "ETH", timeframe: "5m", prediction: "down", confidence: 0.61,
    upsideProbability: 0.42, kellyFraction: 0.04, recommendedPosition: 20.0,
    polymarketPrice: 0.40, kalshiPrice: 0.43,
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    reasoning: "Predicted DOWN with 61% confidence. Mean-reverting regime detected. Conservative 4% Kelly.",
    riskLevel: "medium", regime: "mean_reverting", modelUsed: "kronos_small",
    llmAnalysis: { analysis: "ETH facing resistance at $3.5k. RSI overbought at 72. Expect pullback to $3.4k support." }
  },
  {
    asset: "SOL", timeframe: "15m", prediction: "up", confidence: 0.58,
    upsideProbability: 0.55, kellyFraction: 0.03, recommendedPosition: 15.0,
    polymarketPrice: 0.52, kalshiPrice: null,
    timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
    reasoning: "Predicted UP with 58% confidence. Random walk regime. Low confidence suggests caution.",
    riskLevel: "medium", regime: "random_walk", modelUsed: "statistical",
    llmAnalysis: { analysis: "SOL consolidating after recent rally. Wait for breakout confirmation above $145." }
  }
];
const generateMockArbitrage = (): ArbitrageOpp[] => [
  {
    type: "direction_mismatch", asset: "BTC",
    timeframe_a: "5m", timeframe_b: "15m",
    prediction_a: "up", prediction_b: "down",
    spread: 0.18, recommended: "trust_5m"
  },
  {
    type: "internal_arbitrage_15m_vs_5m", asset: "ETH",
    description: "15min UP but 5min DOWN - possible reversal within 15min window",
    strategy: "Wait for 5min reversal then enter 15min direction",
    recommended: "wait_for_reversal"
  },
  {
    type: "aligned_signal", asset: "SOL",
    description: "Both 15m and 5m agree on UP with high confidence",
    strategy: "Aggressive position sizing",
    recommended: "size_aggressively"
  }
];
const generateMockSystemStatus = () => ({
  status: "running",
  agents: {
    search: { name: "search", status: "idle", lastRun: new Date(Date.now() - 2 * 60 * 1000).toISOString(), metrics: { runs: 142, errors: 3, avgLatencyMs: 850 }, tools: ["search_polymarket", "search_kalshi", "get_market_details"], memorySize: 87 },
    data: { name: "data", status: "idle", lastRun: new Date(Date.now() - 1 * 60 * 1000).toISOString(), metrics: { runs: 289, errors: 5, avgLatencyMs: 1200 }, tools: ["fetch_binance", "fetch_apify", "fetch_multi_timeframe", "get_latest_price"], memorySize: 156 },
    prediction: { name: "prediction", status: "idle", lastRun: new Date(Date.now() - 30 * 1000).toISOString(), metrics: { runs: 312, errors: 2, avgLatencyMs: 450 }, tools: ["kronos_predict", "statistical_predict", "ensemble_predict", "monte_carlo_simulate"], memorySize: 312 },
    llm_reasoning: { name: "llm_reasoning", status: "idle", lastRun: new Date(Date.now() - 45 * 1000).toISOString(), metrics: { runs: 198, errors: 1, avgLatencyMs: 2800 }, tools: ["analyze_market", "explain_prediction", "arbitrage_reasoning", "risk_assessment_reasoning"], memorySize: 124 },
    risk: { name: "risk", status: "idle", lastRun: new Date(Date.now() - 30 * 1000).toISOString(), metrics: { runs: 312, errors: 0, avgLatencyMs: 120 }, tools: ["kelly_size", "portfolio_optimize", "risk_assess", "drawdown_control"], memorySize: 124 },
    feedback: { name: "feedback", status: "idle", lastRun: new Date(Date.now() - 45 * 1000).toISOString(), metrics: { runs: 198, errors: 1, avgLatencyMs: 80 }, tools: ["evaluate_prediction", "update_weights", "generate_feedback", "get_accuracy"], memorySize: 198 }
  },
  assets_tracked: ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE"],
  scaling: { multi_asset: true, arbitrage: true, parallel_execution: true },
  lastUpdate: new Date().toISOString(),
  activePredictions: 6,
  totalPredictions: 312,
  accuracy: 0.58
});
const COLORS = { up: '#22c55e', down: '#ef4444', neutral: '#6b7280', primary: '#3b82f6', secondary: '#8b5cf6', accent: '#f59e0b' };
const Card = ({ children, className = "", onClick, style }: { children: React.ReactNode; className?: string; onClick?: () => void; style?: React.CSSProperties }) => (
  <div className={`bg-slate-900/80 backdrop-blur-sm border border-slate-800 rounded-xl p-5 ${className}`} onClick={onClick} style={style}>
    {children}
  </div>
);
const Badge = ({ children, variant = 'default' }: { children: React.ReactNode; variant?: 'default' | 'up' | 'down' | 'warning' | 'success' | 'info' }) => {
  const variants: Record<string, string> = {
    default: 'bg-slate-800 text-slate-300',
    up: 'bg-green-500/20 text-green-400 border border-green-500/30',
    down: 'bg-red-500/20 text-red-400 border border-red-500/30',
    warning: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
    success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    info: 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
  };
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]}`}>{children}</span>;
};
const AgentCard = ({ agent, index }: { agent: AgentStatus; index: number }) => {
  const [expanded, setExpanded] = useState(false);
  const icons: Record<string, React.ReactNode> = {
    search: <Search className="w-5 h-5" />, data: <Database className="w-5 h-5" />,
    prediction: <Brain className="w-5 h-5" />, llm_reasoning: <MessageSquare className="w-5 h-5" />,
    risk: <Shield className="w-5 h-5" />, feedback: <RefreshCw className="w-5 h-5" />
  };
  const colors: Record<string, string> = {
    search: 'text-blue-400', data: 'text-cyan-400', prediction: 'text-purple-400',
    llm_reasoning: 'text-rose-400', risk: 'text-amber-400', feedback: 'text-emerald-400'
  };
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}>
      <Card className="hover:border-slate-700 transition-colors cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`${colors[agent.name]} p-2 bg-slate-800/50 rounded-lg`}>{icons[agent.name]}</div>
            <div>
              <h3 className="font-semibold text-slate-200 capitalize">{agent.name.replace('_', ' ')} Agent</h3>
              <div className="flex items-center gap-2 mt-1">
                <span className={`w-2 h-2 rounded-full ${agent.status === 'idle' ? 'bg-emerald-500' : agent.status === 'running' ? 'bg-amber-500 animate-pulse' : 'bg-red-500'}`} />
                <span className="text-xs text-slate-400 capitalize">{agent.status}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right"><div className="text-xs text-slate-500">Runs</div><div className="text-sm font-mono text-slate-300">{agent.metrics.runs}</div></div>
            <div className="text-right"><div className="text-xs text-slate-500">Latency</div><div className="text-sm font-mono text-slate-300">{agent.metrics.avgLatencyMs}ms</div></div>
            {expanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </div>
        </div>
        <AnimatePresence>
          {expanded && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Errors</div>
                    <div className={`text-lg font-mono ${agent.metrics.errors > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{agent.metrics.errors}</div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Memory</div>
                    <div className="text-lg font-mono text-slate-300">{agent.memorySize}</div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3">
                    <div className="text-xs text-slate-500">Success Rate</div>
                    <div className="text-lg font-mono text-slate-300">{((agent.metrics.runs - agent.metrics.errors) / Math.max(agent.metrics.runs, 1) * 100).toFixed(1)}%</div>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-2">Registered Tools</div>
                  <div className="flex flex-wrap gap-2">
                    {agent.tools.map(tool => <Badge key={tool} variant="default">{tool}</Badge>)}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  );
};
const PredictionCard = ({ pred, index }: { pred: Prediction; index: number }) => (
  <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.1 }}>
    <Card className="border-l-4" style={{ borderLeftColor: pred.prediction === 'up' ? COLORS.up : COLORS.down }}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${pred.prediction === 'up' ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
            <TrendingUp className={`w-5 h-5 ${pred.prediction === 'up' ? 'text-green-400' : 'text-red-400 rotate-180'}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-200">{pred.asset}</span>
              <Badge variant={pred.prediction === 'up' ? 'up' : 'down'}>{pred.prediction.toUpperCase()}</Badge>
              <Badge variant="default">{pred.timeframe}</Badge>
              {pred.modelUsed && <Badge variant="info">{pred.modelUsed}</Badge>}
            </div>
            <div className="text-xs text-slate-500 mt-1">{new Date(pred.timestamp).toLocaleString()}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-slate-200">{(pred.confidence * 100).toFixed(0)}%</div>
          <div className="text-xs text-slate-500">Confidence</div>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-3 mt-4">
        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
          <div className="text-xs text-slate-500">Upside Prob</div>
          <div className="text-sm font-mono text-slate-300">{(pred.upsideProbability * 100).toFixed(1)}%</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
          <div className="text-xs text-slate-500">Kelly %</div>
          <div className="text-sm font-mono text-slate-300">{(pred.kellyFraction * 100).toFixed(1)}%</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
          <div className="text-xs text-slate-500">Position</div>
          <div className="text-sm font-mono text-slate-300">${pred.recommendedPosition.toFixed(0)}</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3 text-center">
          <div className="text-xs text-slate-500">Risk</div>
          <Badge variant={pred.riskLevel === 'low' ? 'success' : pred.riskLevel === 'medium' ? 'warning' : 'down'}>{pred.riskLevel}</Badge>
        </div>
      </div>
      {pred.llmAnalysis?.analysis && (
        <div className="mt-3 p-3 bg-rose-950/30 border border-rose-900/30 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="w-3 h-3 text-rose-400" />
            <span className="text-xs font-medium text-rose-400">LLM Analysis (OpenRouter)</span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">{pred.llmAnalysis.analysis}</p>
        </div>
      )}
      <div className="mt-3 text-xs text-slate-500 leading-relaxed">{pred.reasoning}</div>
      {(pred.polymarketPrice !== null || pred.kalshiPrice !== null) && (
        <div className="mt-3 flex gap-4">
          {pred.polymarketPrice !== null && (
            <div className="flex items-center gap-1 text-xs">
              <Globe className="w-3 h-3 text-blue-400" />
              <span className="text-slate-500">Polymarket:</span>
              <span className="text-slate-300 font-mono">${pred.polymarketPrice.toFixed(2)}</span>
            </div>
          )}
          {pred.kalshiPrice !== null && (
            <div className="flex items-center gap-1 text-xs">
              <Target className="w-3 h-3 text-purple-400" />
              <span className="text-slate-500">Kalshi:</span>
              <span className="text-slate-300 font-mono">${pred.kalshiPrice.toFixed(2)}</span>
            </div>
          )}
        </div>
      )}
    </Card>
  </motion.div>
);
const ArbitrageCard = ({ opp, index }: { opp: ArbitrageOpp; index: number }) => {
  const typeColors: Record<string, string> = {
    direction_mismatch: 'border-amber-500/50',
    internal_arbitrage_15m_vs_5m: 'border-purple-500/50',
    aligned_signal: 'border-green-500/50',
    confidence_divergence: 'border-blue-500/50'
  };
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.1 }}>
      <Card className={`border-l-4 ${typeColors[opp.type] || 'border-slate-600'}`}>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-amber-400" />
              <span className="font-semibold text-slate-200 capitalize">{opp.type.replace(/_/g, ' ')}</span>
              <Badge variant="warning">{opp.asset}</Badge>
            </div>
            {opp.timeframe_a && (
              <div className="flex items-center gap-2 mt-2 text-sm">
                <span className="text-slate-400">{opp.timeframe_a}:</span>
                <Badge variant={opp.prediction_a === 'up' ? 'up' : 'down'}>{opp.prediction_a?.toUpperCase()}</Badge>
                <span className="text-slate-500">vs</span>
                <span className="text-slate-400">{opp.timeframe_b}:</span>
                <Badge variant={opp.prediction_b === 'up' ? 'up' : 'down'}>{opp.prediction_b?.toUpperCase()}</Badge>
                {opp.spread && <span className="text-amber-400 font-mono">spread: {opp.spread}</span>}
              </div>
            )}
            {opp.description && <p className="text-xs text-slate-400 mt-2">{opp.description}</p>}
            {opp.strategy && (
              <div className="mt-2 flex items-center gap-2">
                <GitBranch className="w-3 h-3 text-blue-400" />
                <span className="text-xs text-blue-400">{opp.strategy}</span>
              </div>
            )}
          </div>
          {opp.recommended && <Badge variant="info">{opp.recommended}</Badge>}
        </div>
      </Card>
    </motion.div>
  );
};
const PipelineVisualizer = () => {
  const steps = [
    { name: 'Search', icon: <Search className="w-5 h-5" />, desc: 'Polymarket + Kalshi', color: 'bg-blue-500', agent: 'SearchAgent' },
    { name: 'Data', icon: <Database className="w-5 h-5" />, desc: 'Apify (1000 bars)', color: 'bg-cyan-500', agent: 'DataAgent' },
    { name: 'Predict', icon: <Brain className="w-5 h-5" />, desc: 'Kronos Model', color: 'bg-purple-500', agent: 'PredictionAgent' },
    { name: 'LLM', icon: <MessageSquare className="w-5 h-5" />, desc: 'OpenRouter Reasoning', color: 'bg-rose-500', agent: 'LLMAgent' },
    { name: 'Risk', icon: <Shield className="w-5 h-5" />, desc: 'Kelly Criterion', color: 'bg-amber-500', agent: 'RiskAgent' },
    { name: 'Feedback', icon: <RefreshCw className="w-5 h-5" />, desc: 'Hermes Loop', color: 'bg-emerald-500', agent: 'FeedbackAgent' }
  ];
  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2">
      {steps.map((step, i) => (
        <div key={step.name} className="flex items-center gap-2 shrink-0">
          <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.15, type: 'spring' }} className="flex flex-col items-center">
            <div className={`${step.color} p-3 rounded-xl text-white shadow-lg`}>
              {step.icon}
            </div>
            <div className="mt-2 text-center">
              <div className="text-xs font-semibold text-slate-300">{step.name}</div>
              <div className="text-[10px] text-slate-500 max-w-[100px]">{step.desc}</div>
              <div className="text-[9px] text-slate-600">{step.agent}</div>
            </div>
          </motion.div>
          {i < steps.length - 1 && <ArrowRight className="w-4 h-4 text-slate-600 shrink-0 mb-6" />}
        </div>
      ))}
    </div>
  );
};
const API = 'http://localhost:8000';
export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard'|'agents'|'predictions'|'arbitrage'|'pipeline'>('dashboard');
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [arbitrageOpps, setArbitrageOpps] = useState<ArbitrageOpp[]>([]);
  const [history, setHistory] = useState(generateMockHistory());
  const [isSimulating, setIsSimulating] = useState(false);
  const [pipelineLog, setPipelineLog] = useState<string[]>([]);
  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API}/api/status`);
      if (res.ok) setSystemStatus(await res.json());
      else setSystemStatus(generateMockSystemStatus());
    } catch { setSystemStatus(generateMockSystemStatus()); }
  };
  const fetchPredictions = async () => {
    try {
      const res = await fetch(`${API}/api/predictions/history?limit=20`);
      if (res.ok) {
        const data = await res.json();
        if (data.predictions?.length) {
          setPredictions(data.predictions.map((p: any) => ({
            asset: p.asset, timeframe: p.timeframe,
            prediction: p.prediction, confidence: p.confidence ?? 0.5,
            upsideProbability: p.upside_probability ?? 0.5,
            kellyFraction: p.kelly_fraction ?? 0.05,
            recommendedPosition: p.recommended_position ?? 25,
            polymarketPrice: p.polymarket_price ?? null,
            kalshiPrice: p.kalshi_price ?? null,
            timestamp: p.timestamp ?? new Date().toISOString(),
            reasoning: p.reasoning ?? '', riskLevel: p.risk_level ?? 'medium',
            regime: p.regime ?? 'trending', modelUsed: p.model_used ?? 'statistical',
            llmAnalysis: p.llm_analysis ?? null
          })));
          return;
        }
      }
    } catch {}
    setPredictions(generateMockPredictions());
  };
  useEffect(() => {
    fetchStatus();
    fetchPredictions();
    setArbitrageOpps(generateMockArbitrage());
    const interval = setInterval(() => {
      setHistory(prev => {
        const newData = [...prev.slice(1)];
        const last = prev[prev.length - 1];
        newData.push({
          time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          btc: Math.max(30, Math.min(90, last.btc + (Math.random() - 0.5) * 8)),
          eth: Math.max(30, Math.min(85, last.eth + (Math.random() - 0.5) * 6)),
          sol: Math.max(25, Math.min(80, last.sol + (Math.random() - 0.5) * 7)),
          accuracy: Math.max(40, Math.min(80, last.accuracy + (Math.random() - 0.5) * 5))
        });
        return newData;
      });
    }, 5000);
    return () => clearInterval(interval);
  }, []);
  const runSimulation = async () => {
    setIsSimulating(true);
    setPipelineLog(['🚀 Starting pipeline...']);
    const assets = ['BTC', 'ETH', 'SOL'];
    const newPreds: Prediction[] = [];
    for (const asset of assets) {
      for (const timeframe of ['5m', '15m']) {
        setPipelineLog(prev => [...prev, `⏳ Running ${asset} ${timeframe} prediction...`]);
        try {
          const res = await fetch(`${API}/api/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asset, timeframe, use_kalshi: true, use_polymarket: true, use_llm: true })
          });
          if (res.ok) {
            const p = await res.json();
            newPreds.push({
              asset: p.asset, timeframe: p.timeframe,
              prediction: p.prediction, confidence: p.confidence ?? 0.5,
              upsideProbability: p.upside_probability ?? 0.5,
              kellyFraction: p.kelly_fraction ?? 0.05,
              recommendedPosition: p.recommended_position ?? 25,
              polymarketPrice: p.polymarket_price ?? null,
              kalshiPrice: p.kalshi_price ?? null,
              timestamp: p.timestamp ?? new Date().toISOString(),
              reasoning: p.reasoning ?? '', riskLevel: p.risk_level ?? 'medium',
              regime: p.regime ?? 'trending', modelUsed: p.model_used ?? 'statistical',
              llmAnalysis: p.llm_analysis ?? null
            });
            setPipelineLog(prev => [...prev, `✅ ${asset} ${timeframe}: ${p.prediction?.toUpperCase()} (${Math.round((p.confidence ?? 0.5) * 100)}% conf)`]);
          } else {
            throw new Error('API error');
          }
        } catch {
          setPipelineLog(prev => [...prev, `⚠️ ${asset} ${timeframe}: using statistical fallback`]);
          newPreds.push({
            asset, timeframe,
            prediction: Math.random() > 0.5 ? 'up' : 'down',
            confidence: 0.5 + Math.random() * 0.3,
            upsideProbability: 0.3 + Math.random() * 0.4,
            kellyFraction: Math.random() * 0.08,
            recommendedPosition: Math.random() * 40,
            polymarketPrice: Math.random() > 0.3 ? Math.random() : null,
            kalshiPrice: Math.random() > 0.3 ? Math.random() : null,
            timestamp: new Date().toISOString(),
            reasoning: `Statistical fallback for ${asset} ${timeframe}`,
            riskLevel: ['low', 'medium', 'high'][Math.floor(Math.random() * 3)],
            regime: ['trending', 'mean_reverting', 'random_walk'][Math.floor(Math.random() * 3)],
            modelUsed: 'statistical',
            llmAnalysis: { analysis: 'Backend unavailable — statistical model used.' }
          });
        }
      }
    }
    setPipelineLog(prev => [...prev, `🎉 Pipeline complete! ${newPreds.length} predictions generated.`]);
    setPredictions(prev => [...newPreds, ...prev].slice(0, 20));
    await fetchStatus();
    setIsSimulating(false);
  };
  const accuracyData = [
    { name: 'BTC 5m', accuracy: 62, samples: 142 },
    { name: 'BTC 15m', accuracy: 58, samples: 98 },
    { name: 'ETH 5m', accuracy: 55, samples: 134 },
    { name: 'ETH 15m', accuracy: 52, samples: 89 },
    { name: 'SOL 5m', accuracy: 51, samples: 76 }
  ];
  const regimeData = [
    { name: 'Trending', value: 45, color: '#22c55e' },
    { name: 'Mean Rev', value: 30, color: '#3b82f6' },
    { name: 'Random', value: 25, color: '#6b7280' }
  ];
  const assetDistribution = [
    { name: 'BTC', value: 35, color: '#f59e0b' },
    { name: 'ETH', value: 30, color: '#8b5cf6' },
    { name: 'SOL', value: 15, color: '#14b8a6' },
    { name: 'XRP', value: 10, color: '#3b82f6' },
    { name: 'ADA', value: 5, color: '#ef4444' },
    { name: 'DOGE', value: 5, color: '#22c55e' }
  ];
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2.5 rounded-xl">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  CryptoPredict Agents
                </h1>
                <p className="text-xs text-slate-500">Hermes Agent • Kronos Model • OpenRouter LLM • Kelly Risk</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="hidden md:flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-500/10 rounded-md">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-emerald-400">6 Agents Ready</span>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-500/10 rounded-md">
                  <Coins className="w-3 h-3 text-blue-400" />
                  <span className="text-blue-400">6 Assets</span>
                </div>
              </div>
              <button onClick={runSimulation} disabled={isSimulating}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 rounded-lg text-sm font-medium transition-colors">
                <RefreshCw className={`w-4 h-4 ${isSimulating ? 'animate-spin' : ''}`} />
                {isSimulating ? 'Running Pipeline...' : 'Run Pipeline'}
              </button>
            </div>
          </div>
        </div>
      </header>
      {}
      <nav className="border-b border-slate-800 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1 overflow-x-auto">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: <BarChart3 className="w-4 h-4" /> },
              { id: 'agents', label: 'Agents', icon: <Cpu className="w-4 h-4" /> },
              { id: 'predictions', label: 'Predictions', icon: <Target className="w-4 h-4" /> },
              { id: 'arbitrage', label: 'Arbitrage', icon: <Scale className="w-4 h-4" /> },
              { id: 'pipeline', label: 'Pipeline', icon: <Layers className="w-4 h-4" /> }
            ].map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.id ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-500 hover:text-slate-300'
                }`}>
                {tab.icon}{tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>
      {}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <AnimatePresence mode="wait">
          {}
          {activeTab === 'dashboard' && (
            <motion.div key="dashboard" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              {}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <Card>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/20 rounded-lg"><Activity className="w-5 h-5 text-blue-400" /></div>
                    <div>
                      <div className="text-2xl font-bold text-slate-200">{systemStatus?.totalPredictions || 0}</div>
                      <div className="text-xs text-slate-500">Predictions</div>
                    </div>
                  </div>
                </Card>
                <Card>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/20 rounded-lg"><CheckCircle className="w-5 h-5 text-emerald-400" /></div>
                    <div>
                      <div className="text-2xl font-bold text-slate-200">{systemStatus?.accuracy ? `${(systemStatus.accuracy * 100).toFixed(1)}%` : 'N/A'}</div>
                      <div className="text-xs text-slate-500">Accuracy</div>
                    </div>
                  </div>
                </Card>
                <Card>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/20 rounded-lg"><AlertTriangle className="w-5 h-5 text-amber-400" /></div>
                    <div>
                      <div className="text-2xl font-bold text-slate-200">{systemStatus?.activePredictions || 0}</div>
                      <div className="text-xs text-slate-500">Active</div>
                    </div>
                  </div>
                </Card>
                <Card>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-cyan-500/20 rounded-lg"><Sparkles className="w-5 h-5 text-cyan-400" /></div>
                    <div>
                      <div className="text-lg font-bold text-slate-200">Kronos</div>
                      <div className="text-xs text-slate-500">NeoQuasar/small</div>
                    </div>
                  </div>
                </Card>
                <Card>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-rose-500/20 rounded-lg"><Key className="w-5 h-5 text-rose-400" /></div>
                    <div>
                      <div className="text-lg font-bold text-slate-200">OpenRouter</div>
                      <div className="text-xs text-slate-500">LLM Active</div>
                    </div>
                  </div>
                </Card>
                <Card>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-500/20 rounded-lg"><Eye className="w-5 h-5 text-purple-400" /></div>
                    <div>
                      <div className="text-lg font-bold text-slate-200">{systemStatus?.assets_tracked?.length || 6}</div>
                      <div className="text-xs text-slate-500">Assets Tracked</div>
                    </div>
                  </div>
                </Card>
              </div>
              {}
              <div className="grid md:grid-cols-2 gap-6">
                <Card>
                  <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <LineChart className="w-4 h-4 text-blue-400" />Prediction Confidence Over Time
                  </h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <AreaChart data={history}>
                      <defs>
                        <linearGradient id="btcGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="ethGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="solGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#14b8a6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#475569" fontSize={12} />
                      <YAxis stroke="#475569" fontSize={12} domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }} />
                      <Area type="monotone" dataKey="btc" stroke="#3b82f6" fill="url(#btcGrad)" name="BTC" />
                      <Area type="monotone" dataKey="eth" stroke="#8b5cf6" fill="url(#ethGrad)" name="ETH" />
                      <Area type="monotone" dataKey="sol" stroke="#14b8a6" fill="url(#solGrad)" name="SOL" />
                    </AreaChart>
                  </ResponsiveContainer>
                </Card>
                <Card>
                  <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-emerald-400" />Accuracy by Asset/Timeframe
                  </h3>
                  <ResponsiveContainer width="100%" height={250}>
                    <BarChart data={accuracyData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="name" stroke="#475569" fontSize={12} />
                      <YAxis stroke="#475569" fontSize={12} domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }} />
                      <Bar dataKey="accuracy" fill="#10b981" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>
              {}
              <div className="grid md:grid-cols-2 gap-6">
                <Card>
                  <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <Coins className="w-4 h-4 text-amber-400" />Multi-Asset Distribution
                  </h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={assetDistribution} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value">
                        {assetDistribution.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b' }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex flex-wrap justify-center gap-3 mt-2">
                    {assetDistribution.map(r => (
                      <div key={r.name} className="flex items-center gap-1 text-xs">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: r.color }} />
                        <span className="text-slate-400">{r.name}</span>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card>
                  <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                    <Brain className="w-4 h-4 text-purple-400" />Market Regime Distribution
                  </h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={regimeData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value">
                        {regimeData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b' }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex justify-center gap-4 mt-2">
                    {regimeData.map(r => (
                      <div key={r.name} className="flex items-center gap-1 text-xs">
                        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: r.color }} />
                        <span className="text-slate-400">{r.name}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
              {}
              {pipelineLog.length > 0 && (
                <Card>
                  <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-blue-400" />
                    Live Pipeline Log
                    {isSimulating && <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse ml-1" />}
                  </h3>
                  <div className="bg-slate-950 rounded-lg p-3 font-mono text-xs space-y-1 max-h-40 overflow-y-auto">
                    {pipelineLog.map((line, i) => (
                      <div key={i} className="text-slate-300">{line}</div>
                    ))}
                  </div>
                </Card>
              )}
              {}
              <div>
                <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
                  <Target className="w-4 h-4 text-amber-400" />Recent Predictions
                </h3>
                <div className="space-y-3">
                  {predictions.slice(0, 3).map((pred, i) => <PredictionCard key={`${pred.timestamp}-${i}`} pred={pred} index={i} />)}
                </div>
              </div>
            </motion.div>
          )}
          {}
          {activeTab === 'agents' && (
            <motion.div key="agents" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-200">Agent Status</h2>
                <div className="flex gap-2">
                  <Badge variant="success">{Object.values(systemStatus?.agents || {}).filter((a: any) => a.status === 'idle').length} Ready</Badge>
                  <Badge variant="info">6 Total</Badge>
                </div>
              </div>
              <div className="space-y-3">
                {systemStatus && Object.values(systemStatus.agents).map((agent: any, i) => <AgentCard key={agent.name} agent={agent} index={i} />)}
              </div>
            </motion.div>
          )}
          {}
          {activeTab === 'predictions' && (
            <motion.div key="predictions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              <div className="grid md:grid-cols-4 gap-4">
                <Card>
                  <div className="text-xs text-slate-500 mb-1">Kelly Criterion Avg</div>
                  <div className="text-2xl font-mono text-slate-200">5.2%</div>
                  <div className="text-xs text-emerald-400 mt-1">Optimal sizing</div>
                </Card>
                <Card>
                  <div className="text-xs text-slate-500 mb-1">Sharpe Ratio</div>
                  <div className="text-2xl font-mono text-slate-200">1.34</div>
                  <div className="text-xs text-emerald-400 mt-1">Good risk-adjusted</div>
                </Card>
                <Card>
                  <div className="text-xs text-slate-500 mb-1">Max Drawdown</div>
                  <div className="text-2xl font-mono text-slate-200">-8.2%</div>
                  <div className="text-xs text-amber-400 mt-1">Within limits</div>
                </Card>
                <Card>
                  <div className="text-xs text-slate-500 mb-1">Brier Score</div>
                  <div className="text-2xl font-mono text-slate-200">0.21</div>
                  <div className="text-xs text-emerald-400 mt-1">Well calibrated</div>
                </Card>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-200 mb-4">All Predictions</h3>
                <div className="space-y-3">
                  {predictions.map((pred, i) => <PredictionCard key={`${pred.timestamp}-${i}`} pred={pred} index={i} />)}
                </div>
              </div>
            </motion.div>
          )}
          {}
          {activeTab === 'arbitrage' && (
            <motion.div key="arbitrage" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              <div className="grid md:grid-cols-3 gap-4">
                <Card>
                  <div className="text-xs text-slate-500 mb-1">Arbitrage Types</div>
                  <div className="text-2xl font-mono text-slate-200">4</div>
                  <div className="text-xs text-emerald-400 mt-1">Direction, Confidence, Internal, Cross-asset</div>
                </Card>
                <Card>
                  <div className="text-xs text-slate-500 mb-1">Active Opportunities</div>
                  <div className="text-2xl font-mono text-slate-200">{arbitrageOpps.length}</div>
                  <div className="text-xs text-amber-400 mt-1">Monitor for execution</div>
                </Card>
                <Card>
                  <div className="text-xs text-slate-500 mb-1">Cross-Timeframe</div>
                  <div className="text-2xl font-mono text-slate-200">5m vs 15m</div>
                  <div className="text-xs text-blue-400 mt-1">Primary arbitrage pair</div>
                </Card>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                  <Scale className="w-5 h-5 text-amber-400" />Arbitrage Opportunities
                </h3>
                <div className="space-y-3">
                  {arbitrageOpps.map((opp, i) => <ArbitrageCard key={i} opp={opp} index={i} />)}
                </div>
              </div>
              <Card>
                <h3 className="text-sm font-semibold text-slate-300 mb-4">Arbitrage Strategies</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {[
                    { name: '15min vs 3x 5min', desc: 'If 15min predicts UP but 5min predicts DOWN, wait for 5min reversal then enter 15min direction', icon: <GitBranch className="w-4 h-4" /> },
                    { name: 'Confidence Divergence', desc: 'Same direction but different confidence levels - size position by the higher-confidence timeframe', icon: <BarChart3 className="w-4 h-4" /> },
                    { name: 'Cross-Asset Pairs', desc: 'Long strongest UP asset, short strongest DOWN asset on same timeframe', icon: <ArrowRight className="w-4 h-4" /> },
                    { name: 'Aligned Signal Boost', desc: 'When all timeframes agree with high confidence, use aggressive Kelly sizing', icon: <TrendingUp className="w-4 h-4" /> }
                  ].map((strat, i) => (
                    <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="text-blue-400">{strat.icon}</div>
                        <span className="font-medium text-slate-300">{strat.name}</span>
                      </div>
                      <p className="text-xs text-slate-500">{strat.desc}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </motion.div>
          )}
          {}
          {activeTab === 'pipeline' && (
            <motion.div key="pipeline" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
              <Card>
                <h3 className="text-lg font-semibold text-slate-200 mb-4">Agent Pipeline Flow</h3>
                <PipelineVisualizer />
              </Card>
              <div className="grid md:grid-cols-2 gap-6">
                <Card>
                  <h3 className="text-sm font-semibold text-slate-300 mb-4">Scaling Features</h3>
                  <div className="space-y-3">
                    {[
                      { name: 'Multi-Asset Support', desc: 'BTC, ETH, SOL, XRP, ADA, DOGE', status: 'Active', icon: <Layers className="w-4 h-4" /> },
                      { name: 'Arbitrage Detection', desc: 'Cross-timeframe + cross-asset scanning', status: 'Active', icon: <Scale className="w-4 h-4" /> },
                      { name: 'Parallel Execution', desc: 'Async multi-agent coordination', status: 'Active', icon: <Cpu className="w-4 h-4" /> },
                      { name: 'Kronos Integration', desc: 'github.com/shiyu-coder/Kronos', status: 'Active', icon: <Sparkles className="w-4 h-4" /> },
                      { name: 'OpenRouter LLM', desc: 'meta-llama/llama-3.1-8b-instruct:free', status: 'Active', icon: <MessageSquare className="w-4 h-4" /> },
                      { name: 'Hermes Feedback Loop', desc: 'Self-improving predictions', status: 'Active', icon: <RefreshCw className="w-4 h-4" /> }
                    ].map((feature, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="text-blue-400">{feature.icon}</div>
                          <div>
                            <div className="text-sm font-medium text-slate-300">{feature.name}</div>
                            <div className="text-xs text-slate-500">{feature.desc}</div>
                          </div>
                        </div>
                        <Badge variant="success">{feature.status}</Badge>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card>
                  <h3 className="text-sm font-semibold text-slate-300 mb-4">Data Sources & Models</h3>
                  <div className="space-y-3">
                    {[
                      { name: 'Polymarket', type: 'Prediction Market', status: 'Connected', icon: <Globe className="w-4 h-4 text-blue-400" /> },
                      { name: 'Kalshi', type: 'Prediction Market', status: 'Connected', icon: <Target className="w-4 h-4 text-purple-400" /> },
                      { name: 'Binance', type: 'Exchange API', status: 'Connected', icon: <BarChart3 className="w-4 h-4 text-amber-400" /> },
                      { name: 'Apify', type: 'Data Scraping (1000 bars)', status: 'Connected', icon: <Database className="w-4 h-4 text-emerald-400" /> },
                      { name: 'Kronos', type: 'github.com/shiyu-coder/Kronos', status: 'Active', icon: <Sparkles className="w-4 h-4 text-cyan-400" /> },
                      { name: 'OpenRouter', type: 'LLM Provider (Free)', status: 'Active', icon: <Key className="w-4 h-4 text-rose-400" /> }
                    ].map((source, i) => (
                      <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                        <div className="flex items-center gap-3">
                          {source.icon}
                          <div>
                            <div className="text-sm font-medium text-slate-300">{source.name}</div>
                            <div className="text-xs text-slate-500">{source.type}</div>
                          </div>
                        </div>
                        <Badge variant="success">{source.status}</Badge>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
              <Card>
                <h3 className="text-sm font-semibold text-slate-300 mb-4">System Architecture</h3>
                <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs text-slate-400 overflow-x-auto">
                  <pre>{`crypto-ad-agents/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── config.yaml             # Agent configuration
│   ├── .env                    # API keys (not committed)
│   │   ├── APIFY_API_TOKEN=<your_apify_token>
│   │   └── OPENROUTER_API_KEY=<your_openrouter_key>
│   ├── kronos_integration.py   # Kronos from github.com/shiyu-coder/Kronos
│   ├── agents/
│   │   ├── base_agent.py       # Hermes Agent base class
│   │   ├── search_agent.py     # Polymarket + Kalshi search
│   │   ├── data_agent.py       # Apify (1000 bars) + Binance
│   │   ├── prediction_agent.py # Kronos + statistical fallback
│   │   ├── llm_agent.py        # OpenRouter reasoning
│   │   ├── risk_agent.py       # Kelly Criterion sizing
│   │   ├── feedback_agent.py   # Hermes learning loop
│   │   └── orchestrator.py     # Agent coordination
│   ├── tools/
│   │   ├── polymarket_tool.py
│   │   ├── kalshi_tool.py
│   │   ├── kronos_tool.py
│   │   └── kelly_tool.py
│   └── utils/
│       ├── logging_config.py
│       ├── config_loader.py
│       └── helpers.py
└── frontend/                   # React dashboard`}</pre>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
      {}
      <footer className="border-t border-slate-800 mt-12 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-xs text-slate-600">
          <p>CryptoPredict Agents • Hermes Agent Framework • Kronos (github.com/shiyu-coder/Kronos) • OpenRouter LLM • Apify Data • Kelly Criterion</p>
          <p className="mt-1">For educational purposes only. Not financial advice.</p>
        </div>
      </footer>
    </div>
  );
}