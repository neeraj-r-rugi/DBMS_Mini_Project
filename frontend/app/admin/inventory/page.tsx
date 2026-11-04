'use client';
import { FormEvent, useEffect, useState } from 'react';
import { LockKeyhole, Plus, Trash2 } from 'lucide-react';
import { addAdminInventory, addAdminService, getInventory, removeAdminInventory } from '../../../lib/api';
import { Vehicle } from '../../../lib/types';

export default function AdminInventory() {
  const [password, setPassword] = useState('');
  const [cars, setCars] = useState<Vehicle[]>([]);
  const [message, setMessage] = useState('');
  const [serviceCarId, setServiceCarId] = useState<string | number>('');
  const [service, setService] = useState({ service_date: '', service_cost: 0, service_details: '' });
  const [form, setForm] = useState({ brand: 'Honda', model: 'City', year: 2020, km_driven: 40000, transmission: 'Manual', owner: 'First', fuel_type: 'Petrol', asking_price: 800000, current_condition: 'Good', additional_features: '', accident_history: 'None', service_date: '', service_cost: 0, service_details: '' });
  const refresh = () => getInventory().then(setCars);
  useEffect(() => { const stored = sessionStorage.getItem('admin-password'); if (stored) setPassword(stored); }, []);
  async function authenticate() {
    const value = window.prompt('Admin password');
    if (value) { sessionStorage.setItem('admin-password', value); setPassword(value); }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await addAdminInventory(password, { ...form, metadata: { current_condition: form.current_condition, additional_features: form.additional_features.split(',').map(x => x.trim()).filter(Boolean), accident_history: form.accident_history }, service_history: form.service_date && form.service_details ? [{ service_date: form.service_date, service_cost: form.service_cost, service_details: form.service_details }] : [] });
      setMessage('Car added successfully.'); refresh();
    } catch { setMessage('Authentication failed or the car could not be added.'); }
  }
  async function remove(id: string | number | undefined) {
    if (id == null || !window.confirm('Remove this car from inventory?')) return;
    try { await removeAdminInventory(password, id); setMessage('Car removed.'); refresh(); }
    catch { setMessage('Authentication failed or the car could not be removed.'); }
  }
  async function submitService(event: FormEvent) {
    event.preventDefault();
    if (!serviceCarId || !service.service_date || !service.service_details) return;
    try {
      await addAdminService(password, serviceCarId, service);
      setMessage('Service record added successfully.');
      setService({ service_date: '', service_cost: 0, service_details: '' });
    } catch { setMessage('Could not add the service record.'); }
  }
  if (!password) return <main className="mx-auto max-w-xl px-5 py-20"><div className="card p-8 text-center"><LockKeyhole className="mx-auto text-mint" size={36}/><h1 className="mt-4 text-2xl font-bold">Restricted inventory administration</h1><p className="mt-2 text-sm text-slate-400">This page is not linked from the public navigation.</p><button className="btn-primary mt-6" onClick={authenticate}>Enter admin password</button></div></main>;
  return <main className="mx-auto max-w-6xl px-5 py-10"><div className="mb-8"><p className="text-xs uppercase tracking-widest text-mint">Private admin area</p><h1 className="mt-2 text-3xl font-bold">Manage inventory</h1></div>{message && <p role="status" className="mb-5 rounded-xl border border-mint/30 bg-mint/10 p-3 text-sm">{message}</p>}<form onSubmit={submit} className="card grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4"><input className="field" placeholder="Brand" value={form.brand} onChange={e => setForm({...form, brand: e.target.value})}/><input className="field" placeholder="Model" value={form.model} onChange={e => setForm({...form, model: e.target.value})}/><input className="field" type="number" placeholder="Year" value={form.year} onChange={e => setForm({...form, year: Number(e.target.value)})}/><input className="field" type="number" placeholder="Mileage" value={form.km_driven} onChange={e => setForm({...form, km_driven: Number(e.target.value)})}/><input className="field" placeholder="Transmission" value={form.transmission} onChange={e => setForm({...form, transmission: e.target.value})}/><input className="field" placeholder="Owner" value={form.owner} onChange={e => setForm({...form, owner: e.target.value})}/><input className="field" placeholder="Fuel type" value={form.fuel_type} onChange={e => setForm({...form, fuel_type: e.target.value})}/><input className="field" type="number" placeholder="Asking price" value={form.asking_price} onChange={e => setForm({...form, asking_price: Number(e.target.value)})}/><input className="field" placeholder="Condition" value={form.current_condition} onChange={e => setForm({...form, current_condition: e.target.value})}/><input className="field" placeholder="Features, comma separated" value={form.additional_features} onChange={e => setForm({...form, additional_features: e.target.value})}/><input className="field" placeholder="Accident history" value={form.accident_history} onChange={e => setForm({...form, accident_history: e.target.value})}/><div className="col-span-full border-t border-line pt-4"><p className="mb-3 text-sm font-semibold">Optional first service record</p><div className="grid gap-4 sm:grid-cols-3"><input className="field" type="date" value={form.service_date} onChange={e => setForm({...form, service_date: e.target.value})}/><input className="field" type="number" min="0" placeholder="Service cost" value={form.service_cost} onChange={e => setForm({...form, service_cost: Number(e.target.value)})}/><input className="field" placeholder="Service details" value={form.service_details} onChange={e => setForm({...form, service_details: e.target.value})}/></div></div><button className="btn-primary"><Plus size={17}/>Add car</button></form><form onSubmit={submitService} className="card mt-6 grid gap-4 p-6 sm:grid-cols-4"><select className="field" value={serviceCarId} onChange={e => setServiceCarId(e.target.value)}><option value="">Select existing car</option>{cars.map(car => <option key={car.id} value={car.id}>{car.Brand} {car.model} — #{car.id}</option>)}</select><input className="field" type="date" required value={service.service_date} onChange={e => setService({...service, service_date: e.target.value})}/><input className="field" type="number" min="0" placeholder="Service cost" required value={service.service_cost} onChange={e => setService({...service, service_cost: Number(e.target.value)})}/><div className="flex gap-2"><input className="field" placeholder="Service details" required value={service.service_details} onChange={e => setService({...service, service_details: e.target.value})}/><button className="btn-primary shrink-0">Add service</button></div></form><div className="mt-8 space-y-3">{cars.map(car => <div className="card flex items-center justify-between p-4" key={car.id}><div><p className="font-semibold">{car.Brand} {car.model}</p><p className="text-sm text-slate-400">{car.Year} · {car.AskPrice}</p></div><button className="rounded-lg p-2 text-red-300 hover:bg-red-400/10" aria-label={`Remove ${car.Brand} ${car.model}`} onClick={() => remove(car.id)}><Trash2 size={18}/></button></div>)}</div></main>;
}
