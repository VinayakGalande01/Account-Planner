'use client';

import React from 'react';

interface BracketsProps {
  className?: string;
  children?: React.ReactNode;
}

export const Brackets: React.FC<BracketsProps> = ({ className = '', children }) => (
  <div className={`brackets ${className}`}>
    <span className="br-tr" />
    <span className="br-bl" />
    {children}
  </div>
);
