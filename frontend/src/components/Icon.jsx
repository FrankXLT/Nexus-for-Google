import React from 'react';

const Icon = ({ name, className = "w-6 h-6" }) => {
    const src = new URL(`../assets/images/${name}.svg`, import.meta.url).href;
    return (
        <img src={src} className={className} alt={name} />
    );
};

export default Icon;