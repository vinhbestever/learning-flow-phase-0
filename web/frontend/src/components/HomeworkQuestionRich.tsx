/**
 * Renders LMS homework media (images / listen audio) extracted at export time.
 * URLs are plain strings from the pipeline — only used as img/audio src.
 */

export interface ChoicePreview {
  letter?: string
  text: string | null
  image_urls: string[]
  audio_urls: string[]
}

function MediaStrip({ urls, label }: { urls: string[]; label: string }) {
  if (!urls.length) return null
  return (
    <div className="mt-2">
      <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-2)]">
        {label}
      </p>
      <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:thin]">
        {urls.map((src, i) => (
          <figure
            key={`${src}-${i}`}
            className="group relative shrink-0 overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-[0_6px_20px_-8px_rgba(26,35,51,0.12)]"
            style={{
              transform: i % 2 === 0 ? 'rotate(-0.6deg)' : 'rotate(0.5deg)',
            }}
          >
            <img
              src={src}
              alt=""
              loading="lazy"
              decoding="async"
              referrerPolicy="no-referrer"
              className="h-24 w-24 object-contain p-1 transition duration-300 group-hover:scale-[1.03] sm:h-28 sm:w-28"
            />
            <figcaption className="sr-only">{label} {i + 1}</figcaption>
          </figure>
        ))}
      </div>
    </div>
  )
}

function AudioList({ urls }: { urls: string[] }) {
  if (!urls.length) return null
  return (
    <ul className="mt-2 space-y-1.5">
      {urls.map((src, i) => (
        <li key={`${src}-${i}`} className="rounded-md border border-[var(--mint)]/25 bg-[var(--mint-soft)]/40 px-2 py-1">
          <audio controls preload="none" className="h-8 w-full max-w-md align-middle">
            <source src={src} />
          </audio>
        </li>
      ))}
    </ul>
  )
}

export function HomeworkQuestionRich({
  stemMediaUrls = [],
  commentMediaUrls = [],
  choicePreviews = [],
}: {
  stemMediaUrls?: string[]
  commentMediaUrls?: string[]
  choicePreviews?: ChoicePreview[]
}) {
  const stemAudio = stemMediaUrls.filter((u) => /\.(mp3|wav|m4a|ogg)(\?|$)/i.test(u))
  const stemImg = stemMediaUrls.filter((u) => !stemAudio.includes(u))
  const commentAudio = commentMediaUrls.filter((u) => /\.(mp3|wav|m4a|ogg)(\?|$)/i.test(u))
  const commentImg = commentMediaUrls.filter((u) => !commentAudio.includes(u))

  const hasChoices = choicePreviews.some(
    (c) => (c.text && c.text.length > 0) || c.image_urls.length > 0 || c.audio_urls.length > 0,
  )

  if (
    !stemImg.length
    && !commentImg.length
    && !stemAudio.length
    && !commentAudio.length
    && !hasChoices
  ) {
    return null
  }

  return (
    <div className="mt-2 rounded-xl border border-[var(--border)]/80 bg-gradient-to-br from-[var(--surface)] via-[var(--void)] to-[var(--mint-soft)]/25 p-3 shadow-inner">
      <MediaStrip urls={stemImg} label="Đề bài (hình)" />
      <AudioList urls={stemAudio} />
      {commentImg.length > 0 && <MediaStrip urls={commentImg} label="Gợi ý / nghe (hình)" />}
      <AudioList urls={commentAudio} />

      {hasChoices && (
        <div className="mt-3 border-t border-[var(--border)]/60 pt-3">
          <p className="mb-2 text-[9px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-2)]">
            Lựa chọn
          </p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {choicePreviews.map((c, idx) => {
              const key = `${c.letter ?? idx}-${c.text ?? ''}`
              if (!c.text && !c.image_urls.length && !c.audio_urls.length) return null
              return (
                <li
                  key={key}
                  className="flex gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)]/90 p-2 shadow-sm"
                >
                  {c.letter && (
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[var(--ink)] text-[11px] font-bold text-white">
                      {c.letter}
                    </span>
                  )}
                  <div className="min-w-0 flex-1">
                    {c.text && <p className="text-[11px] leading-snug text-[var(--ink)]">{c.text}</p>}
                    {c.image_urls.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {c.image_urls.map((src, i) => (
                          <img
                            key={`${src}-${i}`}
                            src={src}
                            alt=""
                            loading="lazy"
                            decoding="async"
                            referrerPolicy="no-referrer"
                            className="h-16 w-16 rounded border border-[var(--border)] object-contain"
                          />
                        ))}
                      </div>
                    )}
                    <AudioList urls={c.audio_urls} />
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
