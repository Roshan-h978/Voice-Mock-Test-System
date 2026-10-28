import Footer from '../../components/Footer';
import Navbar from '../../components/Navbar';
import { APP_NAME } from '../../utils/constants';

const UPDATED = '28 October 2026';

/** Plain-language privacy notice. Linked from the footer and the sign-in pages (and usable in Google's consent screen). */
export default function Privacy() {
  return (
    <>
      <Navbar />
      <main className="vmt-section">
        <article className="vmt-card vmt-prose">
          <header className="vmt-stack vmt-stack-sm">
            <span className="overline">Privacy</span>
            <h1 className="title-lg">How {APP_NAME} uses your information</h1>
            <p className="body-sm vmt-muted">Last updated {UPDATED}</p>
          </header>

          <section>
            <h2 className="title-sm">What we keep</h2>
            <ul>
              <li>Your account: name, email address, English level and, if you add it, a phone number.</li>
              <li>Your password, stored only in a scrambled (hashed) form that nobody can read.</li>
              <li>The voice recordings you submit in speaking tests.</li>
              <li>What we work out from them: a transcript, your scores, feedback and any teacher review.</li>
              <li>If you sign in with Google: the name and email address Google shares with us. We never see your Google password.</li>
            </ul>
          </section>

          <section>
            <h2 className="title-sm">Why we keep it</h2>
            <ul>
              <li>To run your speaking tests, score your answers and show your progress over time.</li>
              <li>So your teachers (the site's admins) can listen to answers that need a closer look and add their review.</li>
              <li>To send account emails only: invitations, password resets and &quot;your review is ready&quot;.</li>
            </ul>
            <p className="body">We don&apos;t sell your information, show adverts or use tracking cookies.</p>
          </section>

          <section>
            <h2 className="title-sm">Who else handles it</h2>
            <ul>
              <li>Our hosting providers store the website, the database and the recordings for us.</li>
              <li>
                When automatic scoring is switched on, your recording is sent to an AI service that turns speech into text and
                writes feedback: Groq, or OpenAI and Anthropic, depending on how this site is set up. If that service is busy, the
                transcript may be sent to Google Gemini instead. They process it to give us the result.
              </li>
              <li>The Google sign-in button is provided by Google and follows Google&apos;s own privacy policy.</li>
            </ul>
          </section>

          <section>
            <h2 className="title-sm">Who can see your results</h2>
            <p className="body">
              Only you and the site&apos;s teachers and admins. Other students can&apos;t see your recordings, scores or profile.
            </p>
          </section>

          <section>
            <h2 className="title-sm">Your choices</h2>
            <ul>
              <li>You can update your name, phone and password on your Profile page at any time.</li>
              <li>You can ask the person who runs this site (your teacher or school) to delete your account and recordings.</li>
              <li>Your browser keeps you signed in using its local storage. Signing out removes this.</li>
            </ul>
          </section>
        </article>
      </main>
      <Footer />
    </>
  );
}
