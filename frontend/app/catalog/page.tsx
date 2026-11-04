'use client';
import { useEffect, useMemo, useState } from 'react';
import { CarFront, Search } from 'lucide-react';
import { PageIntro } from '../../components/Layout';
import { getInventory } from '../../lib/api';
import { Vehicle } from '../../lib/types';

export default function Catalog() {
  const [cars, setCars] = useState<Vehicle[]>([]);
  const [query, setQuery] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  useEffect(() => { getInventory().then(setCars); }, []);
  const filtered = useMemo(() => cars.filter((car) =>
    `${car.Brand} ${car.model}`.toLowerCase().includes(query.toLowerCase()) &&
    (!maxPrice || Number(String(car.AskPrice).replace(/[^\d]/g, '')) <= Number(maxPrice))
  ), [cars, maxPrice, query]);
  return <><PageIntro eyebrow="Public catalog" title="Find your next car." description="Explore available vehicles in the lot and narrow the list by model or budget." />
    <div className="card mb-6 flex flex-col gap-3 p-4 md:flex-row">
      <label className="relative flex-1"><Search className="absolute left-3 top-3 text-slate-500" size={17}/><input className="field pl-10" aria-label="Search cars" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search brand or model..." /></label>
      <input className="field md:w-56" type="number" min="0" aria-label="Maximum budget" value={maxPrice} onChange={e => setMaxPrice(e.target.value)} placeholder="Maximum budget (₹)" />
    </div>
    <p className="mb-4 text-sm text-slate-400">{filtered.length} available vehicles</p>
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{filtered.map(car => <article className="card p-5" key={car.id}><CarFront className="mb-5 text-mint" size={24}/><h2 className="font-bold">{car.Brand} {car.model}</h2><p className="mt-1 text-sm text-slate-400">{car.Year} · {car.kmDriven} · {car.FuelType}</p><p className="mt-5 font-bold text-mint">{car.AskPrice || 'Price on request'}</p></article>)}</div>
  </>;
}
