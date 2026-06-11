import React from 'react';

/**
 * Reusable icon component loading SVGs from assets.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Interactions:
 * - None
 *
 * @param {Object} props - name of the icon and optional className
 * @returns {JSX.Element}
 */
const Icon = ({ name, className = "w-6 h-6" }) => {
    const src = new URL(`../assets/images/${name}.svg`, import.meta.url).href;
    return (
        <img src={src} className={className} alt={name} />
    );
};

export default Icon;