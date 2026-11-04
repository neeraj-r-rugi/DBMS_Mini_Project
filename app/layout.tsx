import './globals.css'; import { Layout } from '../components/Layout';
export const metadata={title:'AutoValue — Used car intelligence',description:'Appraise, manage and explore your used car inventory.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><Layout>{children}</Layout></body></html>}
