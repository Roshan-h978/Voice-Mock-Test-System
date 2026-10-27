import { ArrowRight, Award, Headphones, MessageSquare, Mic, ShieldCheck, TrendingUp } from 'lucide-react';
import Button from '../../components/Button';
import Footer from '../../components/Footer';
import Navbar from '../../components/Navbar';
import ScoreRing from '../../components/ScoreRing';
import SkillBar from '../../components/SkillBar';
import { useAuth } from '../../context/AuthContext';
import { ROLE_HOME } from '../../utils/constants';

const STEPS = [
  {
    title: 'Choose a mock test',
    text: 'Pick a test that matches your level. Each one has a few short speaking questions.',
  },
  {
    title: 'Record your answers',
    text: 'Read the question, take a moment to think, then speak. Listen back and record again if you like.',
  },
  {
    title: 'Get your score and tips',
    text: 'See your fluency, pronunciation and grammar scores, with practical advice for next time.',
  },
];

const FEATURES = [
  { icon: Award, title: 'Three clear scores', text: 'Fluency, pronunciation and grammar, each out of 100.' },
  { icon: MessageSquare, title: 'Teacher review', text: 'Teachers check answers that need a closer look and add their notes.' },
  { icon: TrendingUp, title: 'Track your progress', text: 'Every result is saved, so you can see your speaking improve.' },
  { icon: Headphones, title: 'Hear yourself', text: 'Play back every answer and read a transcript of what you said.' },
  { icon: ShieldCheck, title: 'Private by default', text: 'Only you and your teachers can see your recordings and results.' },
  { icon: Mic, title: 'Works on any device', text: 'Practise on a laptop or a phone, in the browser you already use.' },
];

const SAMPLE_SKILLS = [
  { label: 'Fluency', value: 82 },
  { label: 'Pronunciation', value: 74 },
  { label: 'Grammar', value: 76 },
];

export default function Home() {
  const { user } = useAuth();
  const dashboard = user ? ROLE_HOME[user.role] : null;

  return (
    <>
      <Navbar />
      <main>
        <section className="vmt-hero">
          <div className="vmt-hero-inner">
            <div className="vmt-stack vmt-stack-lg">
              <span className="overline">English speaking practice</span>
              <h1 className="display">Practise speaking. Get clear feedback in seconds.</h1>
              <p className="vmt-hero-lead">
                Take mock speaking tests, record your answers and see exactly what to work on next. Built for students
                preparing for interviews, exams and everyday conversation.
              </p>
              <div className="vmt-row">
                {dashboard ? (
                  <Button to={dashboard} iconRight={ArrowRight}>
                    Go to my dashboard
                  </Button>
                ) : (
                  <>
                    <Button to="/register" iconRight={ArrowRight}>
                      Create free account
                    </Button>
                    <Button to="/login" variant="on-navy">
                      Sign in
                    </Button>
                  </>
                )}
              </div>
            </div>

            <div className="vmt-card vmt-hero-card vmt-stack vmt-stack-lg" aria-label="Example result">
              <div className="vmt-row vmt-row-between">
                <span className="overline vmt-muted">Sample result</span>
                <span className="vmt-badge vmt-badge-ready">Scored</span>
              </div>
              <div className="vmt-row" style={{ gap: 'var(--space-3)' }}>
                <ScoreRing value={78} size="sm" label="Sample overall score" />
                <div className="vmt-stack vmt-stack-sm" style={{ flex: 1, minWidth: 160 }}>
                  <span className="title-md">Good progress</span>
                  <span className="body-sm vmt-muted">Everyday conversation · 5 questions</span>
                </div>
              </div>
              <div className="vmt-stack">
                {SAMPLE_SKILLS.map((skill) => (
                  <SkillBar key={skill.label} label={skill.label} value={skill.value} />
                ))}
              </div>
              <div className="vmt-callout">
                <span className="overline">Tip for next time</span>
                <span className="body-sm">Replace “um” with a short, silent pause while you think.</span>
              </div>
            </div>
          </div>
        </section>

        <section className="vmt-section" aria-labelledby="how-title">
          <div className="vmt-section-head">
            <span className="overline">How it works</span>
            <h2 id="how-title" className="title-lg">
              Three steps to a better speaking score
            </h2>
          </div>
          <div className="vmt-grid-3">
            {STEPS.map((step, index) => (
              <div key={step.title} className="vmt-card vmt-step-card">
                <span className="vmt-step-num" aria-hidden="true">
                  {index + 1}
                </span>
                <h3 className="title-sm">{step.title}</h3>
                <p className="body-sm vmt-muted">{step.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="vmt-section" aria-labelledby="features-title" style={{ paddingTop: 0 }}>
          <div className="vmt-section-head">
            <span className="overline">What you get</span>
            <h2 id="features-title" className="title-lg">
              Everything you need to practise on your own
            </h2>
          </div>
          <div className="vmt-grid-3">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <div key={title} className="vmt-card vmt-card-flat vmt-stack vmt-stack-sm">
                <span className="vmt-feature-icon" aria-hidden="true">
                  <Icon className="vmt-icon" />
                </span>
                <h3 className="title-sm">{title}</h3>
                <p className="body-sm vmt-muted">{text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="vmt-cta">
          <div className="vmt-cta-inner">
            <div className="vmt-stack vmt-stack-sm">
              <h2 className="title-lg">Ready for your first mock test?</h2>
              <p className="body vmt-muted">It takes about five minutes.</p>
            </div>
            <Button to={dashboard || '/register'} iconRight={ArrowRight}>
              {dashboard ? 'Go to my dashboard' : 'Start practising'}
            </Button>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
