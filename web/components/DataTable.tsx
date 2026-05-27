import type { ReactNode } from 'react';
import clsx from 'clsx';

export type Column<T> = {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
  className?: string;
};

type DataTableProps<T> = {
  title: string;
  eyebrow?: string;
  rows: T[];
  columns: Column<T>[];
  emptyLabel?: string;
};

export function DataTable<T>({ title, eyebrow, rows, columns, emptyLabel = 'Nenhum registro encontrado.' }: DataTableProps<T>) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          {eyebrow ? <p className="text-xs font-bold uppercase text-amber-700">{eyebrow}</p> : null}
          <h2 className="font-display text-2xl font-bold text-stone-950">{title}</h2>
        </div>
        <span className="rounded-full bg-stone-950 px-3 py-1 text-xs font-bold text-stone-50">{rows.length} itens</span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-2 text-left text-sm">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={clsx('px-4 py-2 text-xs font-bold uppercase text-stone-500', column.className)}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="rounded-lg bg-stone-100 px-4 py-8 text-center text-stone-500">
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="transition hover:bg-stone-50">
                  {columns.map((column, columnIndex) => (
                    <td
                      key={column.key}
                      className={clsx(
                        'border-y border-stone-100 bg-stone-50/80 px-4 py-4 text-stone-800',
                        columnIndex === 0 && 'rounded-l-lg border-l font-semibold text-stone-950',
                        columnIndex === columns.length - 1 && 'rounded-r-lg border-r',
                        column.className,
                      )}
                    >
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
