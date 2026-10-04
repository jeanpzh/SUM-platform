export function BrandMark() {
  return (
    <div className="flex items-center gap-3" aria-label="SUM, FISI UNMSM">
      <div className="grid size-10 place-items-center rounded-lg bg-card text-foreground">
        <span className="font-display text-[1.15rem] leading-none">S</span>
      </div>
      <div className="leading-tight">
        <p className="font-display text-[1.7rem] leading-none tracking-[-0.05em] text-foreground">
          SUM
        </p>
        <p className="mt-1 text-[0.65rem] font-semibold tracking-[0.12em] text-muted-foreground">
          FISI · UNMSM
        </p>
      </div>
    </div>
  )
}
