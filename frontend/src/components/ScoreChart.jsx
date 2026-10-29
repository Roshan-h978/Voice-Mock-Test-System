import { useEffect, useMemo, useRef, useState } from 'react';
import { formatDate, formatScore } from '../utils/formatters';

/*
 * Scores over time: tests as a line with dots, Quick practice as separate dots.
 * Hover (or arrow keys) moves a crosshair to the nearest result and shows its score.
 * Colours passed the dataviz palette check (lightness, chroma, colour-blind separation, contrast).
 */
const SERIES = {
  test: { label: 'Tests', color: '#008c80' },
  practice: { label: 'Quick practice', color: '#c47f00' },
};
const HEIGHT = 240;
const PAD = { top: 16, right: 48, bottom: 28, left: 40 };
const Y_TICKS = [0, 25, 50, 75, 100];
const TIME_FORMAT = new Intl.DateTimeFormat('en-GB', { hour: 'numeric', minute: '2-digit' });

function useWidth(ref, fallback = 640) {
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const element = ref.current;
    if (!element || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, Math.round(entry.contentRect.width))));
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  return width;
}

export default function ScoreChart({ tests, practice, skill = 'overall', skillLabel = 'Overall' }) {
  const wrapRef = useRef(null);
  const width = useWidth(wrapRef);
  const [active, setActive] = useState(null); // index into `points`

  const points = useMemo(() => {
    const rows = [
      ...tests.map((item) => ({ ...item, kind: 'test' })),
      ...practice.map((item) => ({ ...item, kind: 'practice' })),
    ]
      .filter((item) => item[skill] !== null && item[skill] !== undefined)
      .map((item) => ({ ...item, time: new Date(item.date).getTime(), value: item[skill] }));
    return rows.sort((a, b) => a.time - b.time);
  }, [tests, practice, skill]);

  if (points.length === 0) return null;

  const innerWidth = width - PAD.left - PAD.right;
  const innerHeight = HEIGHT - PAD.top - PAD.bottom;
  const first = points[0].time;
  const last = points[points.length - 1].time;
  const span = last - first;
  const x = (time) => PAD.left + (span ? ((time - first) / span) * innerWidth : innerWidth / 2);
  const y = (value) => PAD.top + innerHeight - (value / 100) * innerHeight;

  const testPoints = points.filter((point) => point.kind === 'test');
  const line = testPoints.map((point, index) => `${index ? 'L' : 'M'}${x(point.time).toFixed(1)},${y(point.value).toFixed(1)}`).join(' ');
  const area = testPoints.length > 1
    ? `${line} L${x(testPoints[testPoints.length - 1].time).toFixed(1)},${y(0)} L${x(testPoints[0].time).toFixed(1)},${y(0)} Z`
    : '';
  const lastTest = testPoints[testPoints.length - 1];

  // Up to 5 date labels, evenly spread; times of day when everything is within a day and a half. No repeats.
  const tickCount = Math.min(5, Math.max(1, Math.floor(innerWidth / 110)));
  const label = (time) => (span < 36 * 3600 * 1000 ? TIME_FORMAT.format(new Date(time)) : formatDate(new Date(time)).replace(/ \d{4}$/, ''));
  const xTicks = (span ? Array.from({ length: tickCount + 1 }, (_, index) => first + (span * index) / tickCount) : [first])
    .map((time) => ({ time, text: label(time) }))
    .filter((tick, index, all) => index === 0 || tick.text !== all[index - 1].text);

  const nearest = (clientX) => {
    const box = wrapRef.current.getBoundingClientRect();
    const pointerX = clientX - box.left;
    let best = 0;
    points.forEach((point, index) => {
      if (Math.abs(x(point.time) - pointerX) < Math.abs(x(points[best].time) - pointerX)) best = index;
    });
    return best;
  };

  const onKeyDown = (event) => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault();
      const step = event.key === 'ArrowRight' ? 1 : -1;
      setActive((index) => Math.min(points.length - 1, Math.max(0, (index ?? (step > 0 ? -1 : points.length)) + step)));
    } else if (event.key === 'Escape') {
      setActive(null);
    }
  };

  const current = active !== null ? points[active] : null;
  const tooltipLeft = current ? Math.min(Math.max(x(current.time), 90), width - 90) : 0;

  return (
    <div className="vmt-chart">
      <div className="vmt-chart-legend" aria-hidden="true">
        {testPoints.length > 0 && (
          <span>
            <i className="vmt-key-line" style={{ background: SERIES.test.color }} /> {SERIES.test.label}
          </span>
        )}
        {points.some((point) => point.kind === 'practice') && (
          <span>
            <i className="vmt-key-dot" style={{ background: SERIES.practice.color }} /> {SERIES.practice.label}
          </span>
        )}
      </div>
      <div
        ref={wrapRef}
        className="vmt-chart-plot"
        tabIndex={0}
        role="img"
        aria-label={`${skillLabel} scores over time. ${points.length} results, latest ${formatScore(points[points.length - 1].value)}. Use the left and right arrow keys to read each result.`}
        onPointerMove={(event) => setActive(nearest(event.clientX))}
        onPointerLeave={() => setActive(null)}
        onKeyDown={onKeyDown}
        onBlur={() => setActive(null)}
      >
        <svg width={width} height={HEIGHT} aria-hidden="true">
          {Y_TICKS.map((tick) => (
            <g key={tick}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(tick)} y2={y(tick)} className="vmt-chart-grid" />
              <text x={PAD.left - 8} y={y(tick)} className="vmt-chart-tick" textAnchor="end" dominantBaseline="middle">
                {tick}
              </text>
            </g>
          ))}
          {xTicks.map((tick) => (
            <text key={tick.time} x={x(tick.time)} y={HEIGHT - 8} className="vmt-chart-tick" textAnchor="middle">
              {tick.text}
            </text>
          ))}
          {area && <path d={area} fill={SERIES.test.color} opacity="0.1" />}
          {testPoints.length > 1 && <path d={line} fill="none" stroke={SERIES.test.color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />}
          {current && <line x1={x(current.time)} x2={x(current.time)} y1={PAD.top} y2={PAD.top + innerHeight} className="vmt-chart-crosshair" />}
          {points.map((point, index) => (
            <circle
              key={`${point.kind}-${point.id}`}
              cx={x(point.time)}
              cy={y(point.value)}
              r={index === active ? 6 : 4.5}
              fill={SERIES[point.kind].color}
              stroke="#ffffff"
              strokeWidth="2"
            />
          ))}
          {lastTest && (
            <text x={x(lastTest.time) + 10} y={y(lastTest.value)} className="vmt-chart-end" dominantBaseline="middle">
              {formatScore(lastTest.value)}
            </text>
          )}
        </svg>
        {current && (
          <div className="vmt-chart-tip" style={{ left: tooltipLeft, top: Math.max(4, y(current.value) - 72) }}>
            <strong className="vmt-num">{formatScore(current.value)}</strong>
            <span>
              <i className={current.kind === 'test' ? 'vmt-key-line' : 'vmt-key-dot'} style={{ background: SERIES[current.kind].color }} />{' '}
              {current.kind === 'test' ? current.title : SERIES.practice.label}
            </span>
            <span className="vmt-muted">
              {formatDate(current.date)}, {TIME_FORMAT.format(new Date(current.date))}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
