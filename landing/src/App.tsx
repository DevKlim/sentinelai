import React, { Suspense } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Shield, Share2, Filter, DatabaseZap } from "lucide-react";
import { Button } from "./components/ui/button";
import Marquee from "./components/ui/tech-marquee";
import { Card, CardHeader, CardTitle, CardContent } from "./components/ui/card";

// Lazily load the Spline component for better performance
const Spline = React.lazy(() => import("@splinetool/react-spline"));

const contentVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring",
      stiffness: 100,
      damping: 15,
      staggerChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
};

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-black text-foreground font-sans flex flex-col overflow-x-hidden">
      {/* The 3D asset is fixed to the background */}
      <div className="fixed top-0 left-0 w-full h-full z-0">
        <Suspense
          fallback={
            <div className="w-full h-full flex items-center justify-center bg-black">
              <p className="text-muted-foreground animate-pulse">
                Loading SentinelAI Network...
              </p>
            </div>
          }
        >
          <Spline
            // This is a new, stable, and visually fitting 3D scene.
            scene="https://prod.spline.design/V-c4S3YV3a1bV2fI/scene.splinecode"
          />
        </Suspense>
      </div>

      <div className="relative z-10">
        <header className="fixed top-0 left-0 right-0 z-50">
          <div className="container mx-auto px-6 py-4 flex justify-between items-center">
            <motion.a
              href="#"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="flex items-center space-x-3"
            >
              <Shield className="w-7 h-7 text-cyan-400" />
              <h1 className="text-xl font-bold tracking-wider">SentinelAI</h1>
            </motion.a>
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <a href="/dashboard">
                <Button
                  variant="outline"
                  className="bg-black/20 border-white/20 backdrop-blur-sm hover:bg-white/10 hover:text-white"
                >
                  Dashboard <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </a>
            </motion.div>
          </div>
        </header>

        <main className="flex-grow">
          {/* Hero Section */}
          <section className="relative w-full h-screen flex items-center justify-center text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.5, ease: "easeOut" }}
              className="max-w-4xl mx-auto px-6"
            >
              <h1 className="text-5xl md:text-7xl font-extrabold mb-6 tracking-tight text-shadow-lg bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-400">
                Transforming Chaos into Clarity
              </h1>
              <p className="text-lg md:text-xl text-muted-foreground mb-12 max-w-2xl mx-auto text-shadow">
                SentinelAI ingests raw 911 incident reports and transforms them
                into structured, actionable EIDO data—powering the next
                generation of emergency response.
              </p>
              <a href="/dashboard">
                <Button
                  size="lg"
                  className="bg-cyan-400 text-black hover:bg-cyan-300 shadow-lg shadow-cyan-500/30"
                >
                  See It In Action <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </a>
            </motion.div>
          </section>

          {/* Start of scrollable content */}
          <div className="bg-black/80 backdrop-blur-lg">
            <section className="py-12">
              <div className="container mx-auto">
                <Marquee />
              </div>
            </section>

            <section id="process" className="py-24">
              <div className="container mx-auto px-6">
                <motion.div
                  className="text-center max-w-3xl mx-auto mb-16"
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, amount: 0.5 }}
                  variants={contentVariants}
                >
                  <motion.h2
                    variants={itemVariants}
                    className="text-4xl font-bold mb-4"
                  >
                    The SentinelAI Process
                  </motion.h2>
                  <motion.p
                    variants={itemVariants}
                    className="text-lg text-muted-foreground"
                  >
                    From an emergency call to trainable data in three automated
                    steps.
                  </motion.p>
                </motion.div>

                <motion.div
                  className="grid md:grid-cols-3 gap-8"
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, amount: 0.3 }}
                  variants={contentVariants}
                >
                  <motion.div variants={itemVariants}>
                    <Card>
                      <CardHeader>
                        <Share2 className="h-8 w-8 text-cyan-400 mb-2" />
                        <CardTitle>1. Ingest Raw Data</CardTitle>
                      </CardHeader>
                      <CardContent>
                        Our system listens to multiple streams of unstructured
                        data, including voice from 911 calls, text messages, and
                        sensor alerts—the digital chaos of an emergency.
                      </CardContent>
                    </Card>
                  </motion.div>
                  <motion.div variants={itemVariants}>
                    <Card>
                      <CardHeader>
                        <Filter className="h-8 w-8 text-cyan-400 mb-2" />
                        <CardTitle>2. AI Agent Analysis</CardTitle>
                      </CardHeader>
                      <CardContent>
                        The SentinelAI core agent analyzes the input, extracting
                        key entities, classifying the incident type, and
                        determining priority, turning noise into a coherent
                        signal.
                      </CardContent>
                    </Card>
                  </motion.div>
                  <motion.div variants={itemVariants}>
                    <Card>
                      <CardHeader>
                        <DatabaseZap className="h-8 w-8 text-cyan-400 mb-2" />
                        <CardTitle>3. Structure as EIDO</CardTitle>
                      </CardHeader>
                      <CardContent>
                        The analyzed data is structured into the standardized
                        EIDO format, creating a clean, machine-readable object
                        that's ready for dashboards and future AI training.
                      </CardContent>
                    </Card>
                  </motion.div>
                </motion.div>
              </div>
            </section>

            <section className="py-24">
              <div className="container mx-auto px-6">
                <motion.div
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, amount: 0.5 }}
                  variants={contentVariants}
                  className="relative bg-gray-900 border border-cyan-500/30 rounded-lg p-12 text-center overflow-hidden"
                >
                  <div className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] bg-[radial-gradient(circle_at_center,_rgba(34,211,238,0.1),transparent_40%)] animate-spin-slow z-0"></div>
                  <div className="relative z-10">
                    <motion.h2
                      variants={itemVariants}
                      className="text-4xl font-bold mb-6"
                    >
                      Enter the Command Center
                    </motion.h2>
                    <motion.p
                      variants={itemVariants}
                      className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto"
                    >
                      Explore the live dashboard to see how SentinelAI provides
                      unparalleled situational awareness for emergency response
                      teams.
                    </motion.p>
                    <motion.div variants={itemVariants}>
                      <a href="/dashboard">
                        <Button
                          size="lg"
                          className="bg-cyan-400 text-black hover:bg-cyan-300 shadow-lg shadow-cyan-500/30"
                        >
                          Launch Dashboard{" "}
                          <ArrowRight className="ml-2 h-4 w-4" />
                        </Button>
                      </a>
                    </motion.div>
                  </div>
                </motion.div>
              </div>
            </section>
          </div>
        </main>

        <footer className="py-8 relative z-10 bg-black">
          <div className="container mx-auto px-6 text-center text-muted-foreground">
            <p>
              &copy; {new Date().getFullYear()} SentinelAI. All rights reserved.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default App;
