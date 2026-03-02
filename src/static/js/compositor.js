window.Compositor = {
  COVER_WIDTH: 3784,
  COVER_HEIGHT: 2777,
  DEFAULT_CX: 2850,
  DEFAULT_CY: 1350,
  DEFAULT_RADIUS: 520,

  async smartComposite({ coverImg, generatedImg, cx, cy, radius }) {
    const canvas = document.createElement('canvas');
    canvas.width = this.COVER_WIDTH;
    canvas.height = this.COVER_HEIGHT;
    const ctx = canvas.getContext('2d');

    const centerX = Number(cx || this.DEFAULT_CX);
    const centerY = Number(cy || this.DEFAULT_CY);
    const r = Number(radius || this.DEFAULT_RADIUS);

    if (coverImg) {
      ctx.drawImage(coverImg, 0, 0, canvas.width, canvas.height);
    }

    if (generatedImg) {
      ctx.save();
      ctx.beginPath();
      ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
      ctx.clip();
      const side = Math.max(generatedImg.naturalWidth || generatedImg.width || 1, generatedImg.naturalHeight || generatedImg.height || 1);
      const sx = ((generatedImg.naturalWidth || generatedImg.width || side) - side) / 2;
      const sy = ((generatedImg.naturalHeight || generatedImg.height || side) - side) / 2;
      ctx.drawImage(generatedImg, sx, sy, side, side, centerX - r, centerY - r, r * 2, r * 2);
      ctx.restore();

      ctx.strokeStyle = 'rgba(197,165,90,0.7)';
      ctx.lineWidth = 10;
      ctx.beginPath();
      ctx.arc(centerX, centerY, r - 2, 0, Math.PI * 2);
      ctx.stroke();
    }

    return canvas;
  },
};
