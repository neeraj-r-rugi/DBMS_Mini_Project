'use client';
import { useEffect, useMemo, useState } from 'react';
import { CarFront, Filter, Loader2, Search, X } from 'lucide-react';
import { PageIntro } from '../../components/Layout';
import { getCarDetails, getInventory } from '../../lib/api';
import { CarDetails, Vehicle } from '../../lib/types';

export default function Inventory() {
  const [cars, setCars] = useState<Vehicle[]>([]);
  const [query, setQuery] = useState('');
  const [fuel, setFuel] = useState('All');
  const [selected, setSelected] = useState<CarDetails | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { getInventory().then(setCars).finally(() => setLoading(false)); }, []);
  const filtered = useMemo(() => cars.filter(c =>
    `${c.Brand} ${c.model}`.toLowerCase().includes(query.toLowerCase()) &&
    (fuel === 'All' || c.FuelType.toLowerCase() === fuel.toLowerCase())
  ), [cars, query, fuel]);
  async function showDetails(car: Vehicle) {
    if (car.id == null) return;
    setSelected(await getCarDetails(car.id));
  }
  return <><PageIntro eyebrow="Fleet workspace" title="Inventory, at a glance." description="Click any vehicle to view its CouchDB condition and service history."/>
    <div className="card mb-6 p-4"><div className="flex flex-col gap-3 md:flex-row"><label className="relative flex-1"><Search className="absolute left-3 top-3 text-slate-500" size={17}/><input aria-label="Search inventory" className="field pl-10" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search make or model..."/></label><label className="relative md:w-48"><Filter className="absolute left-3 top-3 text-slate-500" size={16}/><select aria-label="Filter by fuel" className="field pl-9" value={fuel} onChange={e => setFuel(e.target.value)}><option>All</option><option>Petrol</option><option>Diesel</option><option>Electric</option></select></label></div></div>
    {loading ? <div className="flex justify-center py-20"><Loader2 className="animate-spin text-mint"/></div> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{filtered.map(car => <button className="card p-5 text-left transition hover:-translate-y-1 hover:border-mint" key={car.id} onClick={() => showDetails(car)}><div className="mb-5 flex items-start justify-between"><CarFront className="text-mint" size={22}/><span className="rounded-full bg-cyan/10 px-2.5 py-1 text-[10px] font-bold uppercase text-cyan">{car.status || 'Available'}</span></div><h2 className="font-bold text-white">{car.Brand} {car.model}</h2><p className="mt-1 text-sm text-slate-400">{car.Year} · {car.kmDriven} · {car.Transmission}</p><p className="mt-5 font-bold text-mint">{car.AskPrice || '—'}</p></button>)}</div>}
    {selected && <div className="fixed inset-0 z-30 grid place-items-center bg-black/70 p-5" onClick={() => setSelected(null)}><section className="card max-h-[85vh] w-full max-w-2xl overflow-auto p-6" onClick={e => e.stopPropagation()}><div className="flex items-start justify-between"><div><p className="text-xs uppercase tracking-widest text-mint">Vehicle details</p><h2 className="mt-2 text-2xl font-bold">{String(selected.inventory.brand)} {String(selected.inventory.model)}</h2></div><button aria-label="Close details" onClick={() => setSelected(null)}><X/></button></div><div className="mt-6 grid gap-4 sm:grid-cols-3"><Info label="Condition" value={String(selected.car_metadata?.current_condition ?? 'Not recorded')}/><Info label="Accidents" value={String(selected.car_metadata?.accident_history ?? 'Not recorded')}/><Info label="Features" value={Array.isArray(selected.car_metadata?.additional_features) ? selected.car_metadata.additional_features.join(', ') : 'Not recorded'}/></div><h3 className="mt-8 text-lg font-bold">Service history</h3>{selected.service_history.length ? <div className="mt-3 space-y-3">{selected.service_history.map((service, index) => <div className="rounded-xl border border-line p-4" key={String(service._id ?? index)}><p className="font-semibold">{String(service.service_date ?? 'Date not recorded')}</p><p className="mt-1 text-sm text-slate-400">{String(service.service_details ?? 'No details')}</p><p className="mt-2 text-sm text-mint">₹{String(service.service_cost ?? '—')}</p></div>)}</div> : <p className="mt-3 text-sm text-slate-400">No CouchDB service records have been added for this vehicle.</p>}</section></div>}
  </>;
}
function Info({label, value}: {label: string; value: string}) { return <div className="rounded-xl bg-white/5 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-sm">{value}</p></div>; }
