export type Vehicle = { id?: string | number; Brand: string; model: string; Year: number; kmDriven: string | number; Transmission: string; Owner: string; FuelType: string; AskPrice?: string | number; PostedDate?: string; AdditionInfo?: string; status?: string };
export type AppraisalInput = Pick<Vehicle, 'Brand'|'model'|'Year'|'kmDriven'|'Transmission'|'Owner'|'FuelType'>;
export type AppraisalResult = { estimated_price?: number; price?: number; min_price?: number; max_price?: number; confidence?: number; message?: string };
export const fallbackVehicles: Vehicle[] = [
 { id: 'AU-1042', Brand:'Honda', model:'City', Year:2021, kmDriven:'32,400 km', Transmission:'Manual', Owner:'First', FuelType:'Petrol', AskPrice:'₹ 9,45,000', PostedDate:'Today', status:'Available' },
 { id: 'AU-1038', Brand:'Toyota', model:'Innova Crysta', Year:2019, kmDriven:'58,100 km', Transmission:'Automatic', Owner:'First', FuelType:'Diesel', AskPrice:'₹ 17,80,000', PostedDate:'Yesterday', status:'Available' },
 { id: 'AU-1031', Brand:'Hyundai', model:'Creta', Year:2020, kmDriven:'41,800 km', Transmission:'Automatic', Owner:'Second', FuelType:'Diesel', AskPrice:'₹ 13,25,000', PostedDate:'Oct 14, 2024', status:'Reserved' },
 { id: 'AU-1025', Brand:'Maruti Suzuki', model:'Swift', Year:2018, kmDriven:'66,000 km', Transmission:'Manual', Owner:'First', FuelType:'Petrol', AskPrice:'₹ 6,10,000', PostedDate:'Oct 12, 2024', status:'Available' }
];
export const catalog: Record<string,string[]> = { Honda:['City','Amaze','Jazz','Elevate'], Hyundai:['Creta','i20','Venue','Verna'], Toyota:['Innova Crysta','Fortuner','Glanza','Camry'], 'Maruti Suzuki':['Swift','Baleno','Brezza','Wagon R'], Tata:['Nexon','Punch','Harrier','Tiago'], Volkswagen:['Polo','Virtus','Taigun'] };
