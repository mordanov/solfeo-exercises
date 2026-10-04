// Version 0.12.0 does not provide TypeScript declarations.
declare module "soundfont-player" {
  export interface PlayingNote extends AudioNode {
    source: AudioBufferSourceNode;
    stop(when?: number): void;
  }
  export interface Piano {
    buffers: Record<string, AudioBuffer>;
    play(
      key: string,
      when: number,
      options: { duration: number; gain: number },
    ): PlayingNote | undefined;
  }
  export interface InstrumentOptions {
    nameToUrl: () => string;
    map: (key: string) => string;
    adsr: readonly [number, number, number, number];
  }
  const Soundfont: {
    instrument(
      context: AudioContext,
      name: string,
      options: InstrumentOptions,
    ): Promise<Piano>;
  };
  export default Soundfont;
}
