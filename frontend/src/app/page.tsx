import { SearchBar } from "@/components/SearchBar";
import { Footer } from "@/components/Footer";

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <main className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="text-center mb-10">
          <h1 className="text-5xl font-bold tracking-tight mb-4">
            Cut<span className="text-[var(--color-accent)]">Cost</span>
          </h1>
          <p className="text-xl text-[var(--color-text-secondary)] max-w-lg mx-auto">
            Find the cheapest safe place to buy anything.
          </p>
          <p className="text-sm text-[var(--color-text-secondary)] mt-2">
            Real total cost · Merchant trust · Cross-border comparison
          </p>
        </div>

        <SearchBar />

        <div className="mt-8 flex flex-wrap gap-2 justify-center">
          {[
            { label: "iPhone 16 Pro", url: "/browse?brand=Apple&product_line=iPhone" },
            { label: "Samsung Galaxy S25 Ultra", url: "/browse?q=Samsung+Galaxy+S25+Ultra" },
            { label: "Google Pixel 9 Pro", url: "/browse?q=Google+Pixel+9+Pro" },
            { label: "Browse All", url: "/browse" },
          ].map((example) => (
            <a
              key={example.label}
              href={example.url}
              className="px-3 py-1.5 text-sm rounded-full
                         border border-[var(--color-border)]
                         text-[var(--color-text-secondary)]
                         hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]
                         transition-colors"
            >
              {example.label}
            </a>
          ))}
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-3xl text-center">
          <Feature
            title="True Total Cost"
            description="Price + shipping + duties + VAT + currency conversion. The real number."
          />
          <Feature
            title="Merchant Trust"
            description="We verify merchants and flag suspicious deals so you buy with confidence."
          />
          <Feature
            title="Cross-Border"
            description="Compare prices across countries. Is Amazon.de actually cheaper after customs?"
          />
        </div>
      </main>

      <Footer />
    </div>
  );
}

function Feature({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h3 className="font-semibold mb-1">{title}</h3>
      <p className="text-sm text-[var(--color-text-secondary)]">{description}</p>
    </div>
  );
}
