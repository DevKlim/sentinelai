import React from "react";

const technologies = [
  { name: "React", logo: "/react.svg" },
  { name: "FastAPI", logo: "/fastapi.svg" },
  { name: "Python", logo: "/python.svg" },
  { name: "Docker", logo: "/docker.svg" },
  { name: "PostgreSQL", logo: "/postgres.svg" },
  { name: "Vite", logo: "/vite.svg" },
  { name: "TypeScript", logo: "/ts.svg" },
  { name: "Tailwind CSS", logo: "/tailwind.svg" },
  { name: "Nginx", logo: "/nginx.svg" },
];

const Marquee: React.FC = () => {
  return (
    <div className="w-full inline-flex flex-nowrap overflow-hidden [mask-image:_linear-gradient(to_right,transparent_0,_black_128px,_black_calc(100%-200px),transparent_100%)]">
      <ul className="flex items-center justify-center md:justify-start [&_li]:mx-8 [&_img]:max-w-none animate-marquee">
        {technologies.map((tech) => (
          <li key={tech.name}>
            <img
              src={tech.logo}
              alt={tech.name}
              className="h-10 w-auto object-contain grayscale brightness-150 contrast-50 transition-all duration-300"
            />
          </li>
        ))}
      </ul>
      <ul
        className="flex items-center justify-center md:justify-start [&_li]:mx-8 [&_img]:max-w-none animate-marquee"
        aria-hidden="true"
      >
        {technologies.map((tech) => (
          <li key={`${tech.name}-duplicate`}>
            <img
              src={tech.logo}
              alt={tech.name}
              className="h-10 w-auto object-contain grayscale brightness-150 contrast-50 transition-all duration-300"
            />
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Marquee;
