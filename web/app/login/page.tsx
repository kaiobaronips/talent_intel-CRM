import { redirect } from 'next/navigation';
import { LoginForm } from '@/components/LoginForm';
import { getSessionToken } from '@/lib/session';

export const dynamic = 'force-dynamic';

type LoginPageProps = {
  searchParams: Promise<{ error?: string }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { error } = await searchParams;
  const token = await getSessionToken();
  if (token && !error) {
    redirect('/');
  }

  return (
    <main className="min-h-screen bg-[var(--surface)] px-4 py-10 text-stone-950">
      <section className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1fr_420px]">
        <div>
          <p className="text-xs font-bold uppercase text-amber-700">Talent Intel CRM</p>
          <h1 className="mt-4 max-w-3xl font-display text-5xl font-black leading-none text-stone-950 lg:text-7xl">
            Painel operacional de recrutamento
          </h1>
          <p className="mt-5 max-w-2xl text-lg font-medium leading-8 text-stone-600">
            Acesse candidatos, contatos planejados, automações de IA e histórico da operação em uma visão por empresa.
          </p>
        </div>

        <div className="rounded-lg border border-stone-200 bg-white p-6 shadow-[0_24px_80px_rgba(41,37,36,0.08)]">
          <p className="text-xs font-bold uppercase text-amber-700">Login</p>
          <h2 className="mt-2 text-2xl font-black text-stone-950">Entrar no dashboard</h2>
          {error ? (
            <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-900">
              {decodeURIComponent(error)}
            </p>
          ) : null}
          <div className="mt-6">
            <LoginForm />
          </div>
        </div>
      </section>
    </main>
  );
}
