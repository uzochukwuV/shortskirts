import type { ReactNode } from "react";

type StatItem = {
  label: string;
  value: string;
  hint?: string;
};

type Props = {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  stats?: StatItem[];
  className?: string;
};

export function PageHeader({ eyebrow, title, description, actions, stats, className = "" }: Props) {
  return (
    <section className={`rounded-[24px] border border-border bg-white p-6 md:p-8 ${className}`}>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 rounded-[9999px] border border-border bg-muted px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            {eyebrow}
          </div>
          <div className="space-y-3">
            <h1 className="max-w-3xl text-[42px] font-display leading-[0.94] tracking-[-0.045em] text-foreground md:text-[54px]">
              {title}
            </h1>
            <p className="max-w-2xl text-[15px] leading-7 text-muted-foreground md:text-[16px]">
              {description}
            </p>
          </div>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>

      {stats?.length ? (
        <div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((item) => (
            <div key={item.label} className="rounded-[16px] border border-border bg-muted/30 p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">{item.label}</div>
              <div className="mt-2 text-[30px] font-display leading-none tracking-[-0.04em] text-foreground">{item.value}</div>
              {item.hint ? <div className="mt-2 text-xs leading-5 text-muted-foreground">{item.hint}</div> : null}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
