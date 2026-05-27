import type { ReactNode } from 'react';
import Link from 'next/link';
import clsx from 'clsx';
import { logoutAction } from '@/app/actions';
import { getDefaultTenantId } from '@/lib/api';
import { getPrincipal } from '@/lib/session';

function navItems(activeTenantId: string) {
  return [
    { href: '/', label: 'Visão geral' },
    { href: `/tenants/${activeTenantId}`, label: 'Empresa' },
    { href: '/candidates', label: 'Candidatos' },
    { href: '/interactions', label: 'Contatos' },
    { href: '/members', label: 'Equipe' },
    { href: '/workflows', label: 'Automações' },
    { href: '/audit', label: 'Histórico' },
    { href: '/system', label: 'Saúde do sistema' },
  ];
}

type ShellProps = {
  children: ReactNode;
  offline?: boolean;
  title?: string;
  subtitle?: string;
};

export async function Shell({ children, offline = false, title = 'Talent Intel CRM', subtitle }: ShellProps) {
  const principal = await getPrincipal();
  const activeTenantId = principal.data.tenant_id || getDefaultTenantId();
  const navigation = navItems(activeTenantId);

  return (
    <div className="min-h-screen overflow-hidden bg-[var(--surface)] text-stone-950">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[linear-gradient(180deg,#f7f5f0_0%,#eef4f6_100%)]" />

      <aside className="fixed left-4 top-4 z-20 hidden h-[calc(100vh-2rem)] w-72 flex-col rounded-lg border border-stone-200 bg-white p-5 shadow-sm lg:flex">
        <Link href="/" className="block rounded-lg bg-stone-950 p-5 text-stone-50">
          <p className="text-xs font-bold uppercase text-amber-200">Recrutamento com IA</p>
          <h1 className="mt-4 font-display text-3xl font-black leading-none">Talent Intel CRM</h1>
        </Link>

        <nav className="mt-6 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center justify-between rounded-lg px-4 py-3 text-sm font-bold text-stone-700 transition hover:bg-amber-100 hover:text-stone-950"
            >
              {item.label}
              <span className="h-2 w-2 rounded-full bg-stone-300" />
            </Link>
          ))}
        </nav>

        <div className="mt-4 rounded-lg border border-stone-200 bg-stone-50 p-4">
          <p className="text-xs font-bold uppercase text-stone-500">Conexão</p>
          <div className="mt-2 flex items-center gap-2 text-sm font-bold">
            <span className={clsx('h-2.5 w-2.5 rounded-full', offline ? 'bg-amber-500' : 'bg-emerald-500')} />
            {offline ? 'Usando dados de apoio' : 'Sistema conectado'}
          </div>
          <form action={logoutAction} className="mt-4">
            <button type="submit" className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-black text-stone-700 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700">
              Sair
            </button>
          </form>
        </div>
      </aside>

      <main className="px-4 py-4 lg:ml-80 lg:px-8 lg:py-8">
        <details className="reveal group mb-4 rounded-lg border border-stone-200 bg-white p-3 shadow-sm lg:hidden">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-lg bg-stone-950 px-4 py-3 text-stone-50 marker:hidden">
            <span>
              <span className="block text-xs font-bold uppercase text-amber-200">Talent Intel CRM</span>
              <span className="mt-1 block text-sm font-black">Menu</span>
            </span>
            <span className="text-2xl leading-none transition group-open:rotate-45">+</span>
          </summary>
          <div className="mt-3 grid gap-2">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center justify-between rounded-lg border border-stone-200 bg-white px-4 py-3 text-sm font-black text-stone-800"
              >
                {item.label}
                <span className="h-2 w-2 rounded-full bg-amber-400" />
              </Link>
            ))}
            <div className="mt-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-sm font-black text-stone-700">
                  <span className={clsx('h-2.5 w-2.5 rounded-full', offline ? 'bg-amber-500' : 'bg-emerald-500')} />
                  {offline ? 'Dados de apoio' : 'Sistema conectado'}
                </span>
                <form action={logoutAction}>
                  <button type="submit" className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-black text-stone-700">
                    Sair
                  </button>
                </form>
              </div>
            </div>
          </div>
        </details>

        <header className="reveal mb-8 rounded-lg border border-stone-200 bg-white p-5 shadow-sm lg:p-8">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="text-xs font-bold uppercase text-amber-700">Inteligência de recrutamento</p>
              <h1 className="mt-3 max-w-4xl font-display text-4xl font-black leading-tight text-stone-950 lg:text-5xl">{title}</h1>
              {subtitle ? <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-stone-600">{subtitle}</p> : null}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="rounded-full border border-stone-200 bg-stone-50 px-4 py-2 text-sm font-bold text-stone-700">
                {offline ? 'Dados de apoio' : 'Dados reais atualizados'}
              </div>
            </div>
          </div>
        </header>

        <div className="space-y-6">{children}</div>
      </main>
    </div>
  );
}
