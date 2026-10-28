export default function PrivacyPolicyPage() {
  return (
    <main id="main-content" className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
      <article className="prose prose-lg max-w-none">
        <h1>Privacy Policy</h1>
        <p><strong>Last updated:</strong> October 28, 2026</p>

        <h2>Overview</h2>
        <p>Festivo AI ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our service.</p>

        <h2>Information We Collect</h2>
        <ul>
          <li><strong>Account information:</strong> Email address and authentication details via Firebase Authentication</li>
          <li><strong>Event data:</strong> Information you provide about your events, budgets, timelines, vendors, and tasks</li>
          <li><strong>Usage data:</strong> Basic analytics and usage patterns to improve our service</li>
        </ul>

        <h2>How We Use Your Information</h2>
        <ul>
          <li>To provide and maintain our service</li>
          <li>To authenticate your account and secure your data</li>
          <li>To generate AI-powered suggestions using Google Gemini (with your explicit approval required for all changes)</li>
          <li>To improve our service and user experience</li>
        </ul>

        <h2>Data Storage and Security</h2>
        <ul>
          <li>Your data is stored securely using Supabase PostgreSQL with row-level security</li>
          <li>All AI suggestions require explicit user approval before being applied</li>
          <li>We use industry-standard security measures including encryption in transit and at rest</li>
          <li>Authentication is handled securely through Firebase</li>
        </ul>

        <h2>Your Rights</h2>
        <ul>
          <li><strong>Access:</strong> You can view all your event data in your dashboard</li>
          <li><strong>Delete:</strong> You may request deletion of your account and associated data by contacting us</li>
          <li><strong>Export:</strong> You can export your event data as PDF or CSV</li>
        </ul>

        <h2>Third-Party Services</h2>
        <p>We use the following third-party services:</p>
        <ul>
          <li>Firebase Authentication (Google)</li>
          <li>Supabase (Database)</li>
          <li>Google Gemini API (AI suggestions)</li>
          <li>Vercel (Hosting)</li>
        </ul>

        <h2>Contact</h2>
        <p>For questions about this Privacy Policy, please contact us at support@festivoai.com</p>

        <h2>Changes</h2>
        <p>We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page.</p>
      </article>
    </main>
  )
}
