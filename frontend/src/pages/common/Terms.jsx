import { Link } from 'react-router-dom';
import Footer from '../../components/Footer';
import Navbar from '../../components/Navbar';
import { APP_NAME } from '../../utils/constants';

const UPDATED = '28 October 2026';

/** Plain-language terms of use. Linked from the footer, the sign-up page and Google's consent screen. */
export default function Terms() {
  return (
    <>
      <Navbar />
      <main className="vmt-section">
        <article className="vmt-card vmt-prose">
          <header className="vmt-stack vmt-stack-sm">
            <span className="overline">Terms</span>
            <h1 className="title-lg">Terms of use</h1>
            <p className="body-sm vmt-muted">Last updated {UPDATED}</p>
          </header>

          <section>
            <h2 className="title-sm">What {APP_NAME} is</h2>
            <p className="body">
              {APP_NAME} is a free practice tool for spoken English. You record answers to speaking questions and get scores and
              tips. The scores are automatic estimates to help you practise. They are not an official exam result or a
              certificate.
            </p>
          </section>

          <section>
            <h2 className="title-sm">Your account</h2>
            <ul>
              <li>Use your real name and an email address you can open.</li>
              <li>Keep your password private. One account is for one person.</li>
              <li>The site&apos;s teachers and admins can suspend accounts that break these terms.</li>
            </ul>
          </section>

          <section>
            <h2 className="title-sm">Your recordings</h2>
            <ul>
              <li>Your recordings stay yours.</li>
              <li>
                By submitting an answer, you let us store it, turn it into text, score it and show it to the site&apos;s teachers and
                admins so they can review it.
              </li>
              <li>Only record your own voice, and don&apos;t submit anything offensive or illegal.</li>
            </ul>
          </section>

          <section>
            <h2 className="title-sm">Fair use</h2>
            <ul>
              <li>Don&apos;t try to break, overload or get around the site&apos;s security.</li>
              <li>Don&apos;t try to see other people&apos;s accounts, recordings or results.</li>
              <li>Don&apos;t copy the site&apos;s content automatically (for example with scripts or bots).</li>
            </ul>
          </section>

          <section>
            <h2 className="title-sm">Automatic scoring</h2>
            <p className="body">
              Scores and feedback are produced by software and AI services, and they can be wrong. Teachers may review and change
              them. Don&apos;t use them alone for important decisions such as admissions or hiring.
            </p>
          </section>

          <section>
            <h2 className="title-sm">Availability</h2>
            <p className="body">
              The site runs on free hosting, so it can be slow to start or briefly unavailable. Features may change. The site is
              provided as it is, without guarantees, as far as the law allows.
            </p>
          </section>

          <section>
            <h2 className="title-sm">Changes and questions</h2>
            <p className="body">
              If these terms change, the date at the top changes too. For questions, or to have your account deleted, contact the
              person who runs this site (your teacher or school). How we handle your information is explained in our{' '}
              <Link to="/privacy" className="vmt-link">
                privacy notice
              </Link>
              .
            </p>
          </section>
        </article>
      </main>
      <Footer />
    </>
  );
}
