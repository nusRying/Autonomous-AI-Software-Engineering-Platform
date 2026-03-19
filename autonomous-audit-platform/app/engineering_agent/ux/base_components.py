"""
base_components.py — Reference implementations of "Perfect Components" for the Engineering Agent.
These are used as prompt context to ensure high-fidelity UI generation.
"""

BASE_COMPONENTS = {
    "glass_card": """
<div className="bg-slate-800/70 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
  {children}
</div>
""",
    "primary_button": """
<button className="bg-sky-500 hover:bg-sky-400 text-white font-medium py-2 px-4 rounded-lg transition-all active:scale-95 shadow-lg shadow-sky-500/20">
  {label}
</button>
""",
    "input_field": """
<div className="space-y-1">
  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</label>
  <input 
    type="{type}" 
    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg py-2 px-3 text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/50 transition-all"
    placeholder={placeholder}
  />
</div>
""",
    "status_badge": """
<span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-tighter ${
  status === 'success' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
  status === 'warning' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
  'bg-rose-500/20 text-rose-400 border border-rose-500/30'
}`}>
  {status}
</span>
"""
}
