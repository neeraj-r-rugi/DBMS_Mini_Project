import { AppraisalInput, AppraisalResult, CarDetails, Vehicle, fallbackVehicles } from './types';
const base = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
async function request<T>(path: string, init?: RequestInit): Promise<T> { const response = await fetch(`${base}${path}`, { ...init, headers: { 'Content-Type':'application/json', ...(init?.headers || {}) }, cache:'no-store' }); if (!response.ok) throw new Error(`Request failed (${response.status})`); return response.json(); }
export async function getInventory(): Promise<Vehicle[]> {
  if (!base) return fallbackVehicles;
  try {
    const data = await request<Vehicle[] | {items: Array<Record<string, unknown>>}>('/api/inventory?limit=500');
    const items: Array<Record<string, unknown>> = Array.isArray(data)
      ? data as Array<Record<string, unknown>> : data.items;
    return items.map((item) => ({
      id: item.id as string | number,
      Brand: String(item.Brand ?? item.brand ?? ''),
      model: String(item.model ?? ''),
      Year: Number(item.Year ?? item.year),
      kmDriven: String(item.kmDriven ?? item.km_driven ?? 0),
      Transmission: String(item.Transmission ?? item.transmission ?? ''),
      Owner: String(item.Owner ?? item.owner ?? ''),
      FuelType: String(item.FuelType ?? item.fuel_type ?? ''),
      AskPrice: item.AskPrice == null && item.asking_price == null ? undefined : String(item.AskPrice ?? item.asking_price),
      status: String(item.status ?? 'Available'),
    }));
  } catch { return fallbackVehicles; }
}
export async function getCatalog(): Promise<Record<string,string[]>> { if (!base) return {}; return request<Record<string,string[]>>('/catalog'); }
export async function appraiseVehicle(input: AppraisalInput): Promise<AppraisalResult> {
  return request<AppraisalResult>('/api/appraisals', { method:'POST', body:JSON.stringify({
    brand: input.Brand, model: input.model, year: Number(input.Year), km_driven: Number(input.kmDriven),
    transmission: input.Transmission, owner: input.Owner, fuel_type: input.FuelType,
  }) });
}
export async function getCarDetails(id: string | number): Promise<CarDetails> {
  return request<CarDetails>(`/api/inventory/${id}/details`);
}
function adminHeaders(password: string): HeadersInit {
  return { Authorization: `Basic ${btoa(`admin:${password}`)}` };
}
export async function addAdminInventory(password: string, payload: Record<string, unknown>): Promise<Vehicle> {
  return request<Vehicle>('/api/admin/inventory', { method: 'POST', headers: adminHeaders(password), body: JSON.stringify(payload) });
}
export async function removeAdminInventory(password: string, id: string | number): Promise<void> {
  await request<unknown>(`/api/admin/inventory/${id}`, { method: 'DELETE', headers: adminHeaders(password) });
}
export async function addAdminService(password: string, id: string | number, service: Record<string, unknown>): Promise<void> {
  await request<unknown>(`/api/admin/inventory/${id}/service`, { method: 'POST', headers: adminHeaders(password), body: JSON.stringify(service) });
}
