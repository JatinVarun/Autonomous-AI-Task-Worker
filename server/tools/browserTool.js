/**
 * Simulated Web Browser Tool
 * Allows the autonomous worker to navigate web pages, fetch web data,
 * check public registries, and extract information from internal web portals.
 */

const MOCK_WEB_PAGES = {
  "https://portal.acme-industrial.example.com/status": {
    title: "Acme Industrial Solutions - Customer Billing Portal",
    status: 200,
    body: `
      <html>
        <body>
          <h1>Acme Industrial Solutions Billing Center</h1>
          <p>Vendor Status: Certified Supplier A+</p>
          <p>Current Portal Notice: All invoices for Q4 2024 have been generated.</p>
          <table border="1">
            <tr><th>Invoice #</th><th>Issued</th><th>Amount</th><th>Status</th></tr>
            <tr><td>INV-2024-889</td><td>2024-10-15</td><td>$14,250.00</td><td>UNPAID / PENDING ENTERPRISE AP</td></tr>
            <tr><td>INV-2024-512</td><td>2024-05-10</td><td>$2,400.00</td><td>PAID</td></tr>
          </table>
        </body>
      </html>
    `
  },
  "https://api.fxrates.example.com/latest": {
    title: "Global FX Exchange Rates API",
    status: 200,
    body: JSON.stringify({
      base: "USD",
      date: "2024-10-24",
      rates: {
        EUR: 0.925,
        GBP: 0.772,
        CAD: 1.385,
        JPY: 152.40
      }
    })
  },
  "https://irs.example.gov/ein-verification": {
    title: "Federal Tax ID Verification Portal",
    status: 200,
    body: JSON.stringify({
      verified: true,
      records: {
        "XX-9482103": { legalName: "Acme Industrial Solutions Inc.", status: "ACTIVE_GOOD_STANDING" },
        "US-8837194": { legalName: "Globex Logistics Corp", status: "ACTIVE_GOOD_STANDING" },
        "IN-9948201": { legalName: "Initech Technologies Ltd", status: "VERIFIED" }
      }
    })
  }
};

export const browserTools = {
  browser_navigate_and_extract: {
    name: "browser_navigate_and_extract",
    description: "Navigate to a URL using a simulated headless browser to inspect web pages, fetch portal tables, or query external supplier APIs.",
    parameters: {
      type: "object",
      required: ["url"],
      properties: {
        url: {
          type: "string",
          description: "Target URL to browse (e.g. 'https://portal.acme-industrial.example.com/status' or 'https://api.fxrates.example.com/latest')"
        },
        selector: {
          type: "string",
          description: "Optional CSS selector or extract keyword ('table', 'body', 'text')"
        }
      }
    },
    async execute({ url, selector }) {
      try {
        const page = MOCK_WEB_PAGES[url];
        if (!page) {
          // If not in pre-seeded mock, return a structured simulated response
          return {
            success: true,
            url,
            statusCode: 200,
            renderedContent: `Simulated browser navigated to ${url}. Page loaded successfully (HTTP 200). Content: Standard supplier portal interface.`
          };
        }

        return {
          success: true,
          url,
          statusCode: page.status,
          title: page.title,
          renderedContent: page.body.trim()
        };
      } catch (err) {
        return { success: false, error: `Browser navigation error: ${err.message}` };
      }
    }
  }
};
