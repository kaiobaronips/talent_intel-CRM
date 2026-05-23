import { redirect } from 'next/navigation';
import { getDefaultTenantId } from '@/lib/api';

export default function TenantsPage() {
  redirect(`/tenants/${getDefaultTenantId()}`);
}
