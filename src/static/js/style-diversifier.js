const STYLE_POOL = [
  { id: 'classical-oil', label: 'Classical Oil', modifier: 'Classical oil painting texture, dramatic light, rich brushwork.' },
  { id: 'romantic-landscape', label: 'Romantic Landscape', modifier: 'Romantic landscape mood, sweeping skies, luminous atmosphere.' },
  { id: 'dark-romantic', label: 'Dark Romantic', modifier: 'Dark romantic palette, moody shadows, gothic emotional tension.' },
  { id: 'pre-raphaelite', label: 'Pre-Raphaelite', modifier: 'Pre-Raphaelite detail, jewel-like color, elegant symbolic composition.' },
  { id: 'art-nouveau', label: 'Art Nouveau', modifier: 'Art Nouveau curves, organic ornament, stylized decorative storytelling.' },
  { id: 'ukiyoe', label: 'Ukiyo-e Woodblock', modifier: 'Ukiyo-e woodblock aesthetic, bold outlines, flat color rhythm.' },
  { id: 'film-noir', label: 'Film Noir', modifier: 'Film noir contrast, chiaroscuro tension, cinematic narrative framing.' },
  { id: 'botanical', label: 'Botanical Engraving', modifier: 'Botanical engraving linework, precise crosshatching, scientific elegance.' },
  { id: 'gothic-stained', label: 'Gothic Stained Glass', modifier: 'Gothic stained-glass geometry, luminous panes, ornate medieval mood.' },
  { id: 'impressionist', label: 'Impressionist', modifier: 'Impressionist strokes, color vibration, light-driven atmosphere.' },
  { id: 'expressionist', label: 'Expressionist', modifier: 'Expressionist bold gesture, emotional distortion, high-energy chroma.' },
  { id: 'baroque', label: 'Baroque Drama', modifier: 'Baroque drama, theatrical composition, dynamic light and movement.' },
  { id: 'watercolour', label: 'Delicate Watercolour', modifier: 'Delicate watercolor washes, soft transitions, lyrical atmosphere.' },
  { id: 'symbolist', label: 'Symbolist Dream', modifier: 'Symbolist dream imagery, allegorical forms, poetic surreal mood.' },
  { id: 'renaissance', label: 'Renaissance Fresco', modifier: 'Renaissance fresco tonality, balanced composition, classical figuration.' },
  { id: 'russian-realist', label: 'Russian Realist', modifier: 'Russian realist brush texture, human drama, narrative gravitas.' },
];

function shuffle(items) {
  const arr = [...items];
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

window.StyleDiversifier = {
  STYLE_POOL,
  selectDiverseStyles(count = 1) {
    const n = Math.max(0, Number(count || 0));
    if (n === 0) return [];
    const out = [];
    while (out.length < n) {
      const shuffled = shuffle(STYLE_POOL);
      for (const style of shuffled) {
        out.push(style);
        if (out.length >= n) break;
      }
    }
    return out;
  },

  buildDiversifiedPrompt(title, author, style) {
    return [
      `Create a vivid circular vignette illustration for "${title}" by ${author}.`,
      'Focus on a key dramatic or symbolic moment with centered composition and clear focal subject.',
      style?.modifier || 'Classical engraved illustration with rich color and strong contrast.',
      'Mandatory: no text, no letters, no title design, no banners, no ribbons, no frames, no ornaments.',
      'Output only scene artwork designed to sit behind an ornamental medallion frame.',
    ].join(' ');
  },
};
