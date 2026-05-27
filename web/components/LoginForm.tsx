'use client';

import { useActionState } from 'react';
import { loginAction, type ActionState } from '@/app/actions';

const initialState: ActionState = { ok: false, message: '' };

export function LoginForm() {
  const [state, action, pending] = useActionState(loginAction, initialState);

  return (
    <div className="grid gap-4">
      <a
        href="/auth/google"
        className="flex items-center justify-center gap-3 rounded-lg border border-stone-200 bg-white px-5 py-3 text-sm font-black text-stone-950 transition hover:border-stone-300 hover:bg-stone-50"
      >
        <span className="grid h-5 w-5 place-items-center rounded-full bg-stone-950 text-xs font-black text-white">G</span>
        Entrar com Google
      </a>

      <div className="flex items-center gap-3">
        <span className="h-px flex-1 bg-stone-200" />
        <span className="text-xs font-bold uppercase text-stone-400">ou</span>
        <span className="h-px flex-1 bg-stone-200" />
      </div>

      <form action={action} className="grid gap-4">
        <label className="grid gap-2 text-sm font-bold text-stone-700">
          E-mail
          <input
            name="email"
            type="email"
            autoComplete="email"
            required
            className="rounded-lg border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
          />
        </label>
        <label className="grid gap-2 text-sm font-bold text-stone-700">
          Senha
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="rounded-lg border border-stone-200 bg-white px-4 py-3 font-medium text-stone-950 outline-none transition focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
          />
        </label>
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-stone-950 px-5 py-3 text-sm font-black text-stone-50 transition hover:bg-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pending ? 'Entrando...' : 'Entrar'}
        </button>
        {state.message ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-900">{state.message}</p>
        ) : null}
      </form>
    </div>
  );
}
