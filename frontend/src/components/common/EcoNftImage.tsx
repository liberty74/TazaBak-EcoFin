import React, { useEffect, useState } from 'react';

interface EcoNftImageProps {
  svgContent: string;
  title: string;
  className?: string;
}

export default function EcoNftImage({ svgContent, title, className }: EcoNftImageProps) {
  const [objectUrl, setObjectUrl] = useState<string>('');

  useEffect(() => {
    if (!svgContent) {
      setObjectUrl('');
      return;
    }

    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    setObjectUrl(url);

    // Cleanup on unmount or when svgContent changes to prevent memory leaks
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [svgContent]);

  if (!objectUrl) {
    return (
      <div className={`animate-pulse bg-cream dark:bg-muted ${className}`} />
    );
  }

  return (
    <img 
      src={objectUrl} 
      alt={title} 
      className={className} 
      referrerPolicy="no-referrer"
    />
  );
}
