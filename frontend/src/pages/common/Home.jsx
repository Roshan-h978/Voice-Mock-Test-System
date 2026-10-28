import { ArrowRight, Award, Check, Headphones, MessageSquare, Mic, ShieldCheck, TrendingUp } from 'lucide-react';
import Button from '../../components/Button';
import Footer from '../../components/Footer';
import Navbar from '../../components/Navbar';
import ScoreRing from '../../components/ScoreRing';
import { ScoreArc, SoundRings, Waveform } from '../../components/Shapes';
import SkillBar from '../../components/SkillBar';
import { useAuth } from '../../context/AuthContext';
import { useCountUp, useRevealOnScroll } from '../../hooks/useMotion';
import { ROLE_HOME } from '../../utils/constants';

/*
 * Your own hero photo: save it as frontend/src/assets/hero.jpg (or hero.png / hero.webp) and it
 * appears in the arch frame automatically. Without one, the frame shows the built-in recording picture.
 * A portrait photo (taller than wide) fits best.
 */
const HERO_IMAGES = import.meta.glob('../../assets/hero.{jpg,jpeg,png,webp,avif}', { eager: true, import: 'default' });
const HERO_IMAGE = Object.values(HERO_IMAGES)[0];
const HERO_IMAGE_ALT = 'A student practising English speaking';

const HERO_POINTS = ['Free to use', 'Results in seconds', 'Works on your phone'];

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

const SAMPLE_SCORE = 78;
const SAMPLE_SKILLS = [
  { label: 'Fluency', value: 82 },
  { label: 'Pronunciation', value: 74 },
  { label: 'Grammar', value: 76 },
];

/** What the arch frame shows until a photo is added: the record button mid-answer. */
function RecordingScene() {
  return (
    <div className="vmt-scene" aria-hidden="true">
      <span className="vmt-scene-chip">
        <span className="vmt-scene-dot" />
        Recording 0:42
      </span>
      <div className="vmt-scene-mic">
        <SoundRings className="vmt-scene-rings" rings={4} />
        <span className="vmt-ripple" />
        <span className="vmt-ripple" style={{ animationDelay: '1s' }} />
        <span className="vmt-ripple" style={{ animationDelay: '2s' }} />
        <span className="vmt-scene-button">
          <Mic className="vmt-icon-xl" />
        </span>
      </div>
      <Waveform className="vmt-scene-wave" live />
    </div>
  );
}

export default function Home() {
  const { user } = useAuth();
  const dashboard = user ? ROLE_HOME[user.role] : null;
  const counted = useCountUp({ duration: 1400, delay: 900 }); // the sample score counts up once the card is in
  useRevealOnScroll();

  return (
    <>
      <Navbar />
      <main>
        <section className="vmt-hero">
          <div className="vmt-hero-geo" aria-hidden="true">
            <span className="vmt-dots vmt-hero-dots" />
            <SoundRings className="vmt-hero-rings" rings={5} />
          </div>

          <div className="vmt-hero-inner">
            <div className="vmt-hero-copy">
              <span className="overline">English speaking practice</span>
              <h1 className="vmt-hero-title">
                <span>Practise speaking.</span> <span>Get clear feedback in seconds.</span>
              </h1>
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
              <ul className="vmt-hero-points">
                {HERO_POINTS.map((point) => (
                  <li key={point}>
                    <Check className="vmt-icon-sm" aria-hidden="true" />
                    {point}
                  </li>
                ))}
              </ul>
            </div>

            <div className="vmt-hero-visual">
              <span className="vmt-shape vmt-shape-sun" aria-hidden="true" />
              <span className="vmt-shape vmt-shape-quarter" aria-hidden="true" />
              <figure className="vmt-hero-frame">
                {HERO_IMAGE ? <img src={HERO_IMAGE} alt={HERO_IMAGE_ALT} /> : <RecordingScene />}
              </figure>

              <div className="vmt-card vmt-hero-card" aria-label="Example result">
                <div className="vmt-row vmt-row-between">
                  <span className="overline vmt-teal">Sample result</span>
                  <span className="vmt-badge vmt-badge-ready">Scored</span>
                </div>
                <div className="vmt-hero-card-score">
                  <ScoreRing value={Math.round(SAMPLE_SCORE * counted)} size="sm" label="Sample overall score" />
                  <div className="vmt-stack vmt-stack-sm">
                    {SAMPLE_SKILLS.map((skill) => (
                      <SkillBar key={skill.label} label={skill.label} value={Math.round(skill.value * counted)} />
                    ))}
                  </div>
                </div>
                <div className="vmt-callout">
                  <span className="overline">Tip for next time</span>
                  <span className="body-sm">Replace “um” with a short, silent pause while you think.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="vmt-section vmt-section-after-hero" aria-labelledby="how-title">
          <div className="vmt-section-head vmt-reveal">
            <span className="overline">How it works</span>
            <h2 id="how-title" className="title-lg">
              Three steps to a better speaking score
            </h2>
          </div>
          <ol className="vmt-flow">
            {STEPS.map((step, index) => (
              <li key={step.title} className="vmt-flow-step vmt-reveal" style={{ '--d': `${index * 160}ms` }}>
                <span className="vmt-flow-num" aria-hidden="true">
                  {index + 1}
                </span>
                <div className="vmt-card vmt-flow-card">
                  <h3 className="title-sm">{step.title}</h3>
                  <p className="body-sm vmt-muted">{step.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="vmt-section" aria-labelledby="features-title" style={{ paddingTop: 0 }}>
          <div className="vmt-section-head vmt-reveal">
            <span className="overline">What you get</span>
            <h2 id="features-title" className="title-lg">
              Everything you need to practise on your own
            </h2>
          </div>
          <div className="vmt-grid-3">
            {FEATURES.map(({ icon: Icon, title, text }, index) => (
              <div key={title} className="vmt-card vmt-feature vmt-reveal" style={{ '--d': `${(index % 3) * 100}ms` }}>
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
          <div className="vmt-cta-panel vmt-reveal">
            <div className="vmt-cta-geo" aria-hidden="true">
              <SoundRings className="vmt-cta-rings" rings={4} />
              <ScoreArc className="vmt-cta-arc" value={78} />
              <span className="vmt-shape vmt-cta-sun" />
            </div>
            <div className="vmt-cta-text">
              <h2 className="title-lg">Ready for your first mock test?</h2>
              <p className="body">It takes about five minutes.</p>
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
