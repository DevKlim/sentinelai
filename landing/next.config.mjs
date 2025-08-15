/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  // If you need to serve images from external domains in the future
  // images: {
  //   remotePatterns: [
  //     {
  //       protocol: 'https',
  //       hostname: 'example.com',
  //     },
  //   ],
  // },
  webpack: (config) => {
    config.module.rules.push({
      test: /\.(glb|gltf)$/i,
      type: "asset/resource",
      generator: {
        filename: "static/media/[name].[hash][ext]",
      },
    });
    return config;
  },
};

export default nextConfig;
