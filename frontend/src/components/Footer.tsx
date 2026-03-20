export function Footer() {
  return (
    <footer className="mt-20 py-8 border-t border-[var(--color-border)] text-sm text-[var(--color-text-secondary)]">
      <div className="max-w-3xl mx-auto px-4 space-y-4">
        <p>
          Prices are estimates based on our most recent data. Actual prices may
          differ at checkout. Total costs including shipping, duties, and taxes
          are estimates and may vary. Always verify the final price on the
          merchant&apos;s website before purchasing.
        </p>
        <p>
          CutCost earns affiliate commissions on some links. Affiliate status
          never influences ranking order.
        </p>
        <div className="flex gap-4">
          <span>&copy; {new Date().getFullYear()} CutCost</span>
        </div>
      </div>
    </footer>
  );
}
