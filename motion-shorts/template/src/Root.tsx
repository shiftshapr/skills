import { Composition } from "remotion";
import { ConstellationShort } from "./Constellation";
import { SketchDemo } from "./Sketch";

export const RemotionRoot: React.FC = () => {
  return (
    <>
    <Composition
      id="ConstellationShort"
      component={ConstellationShort}
      durationInFrames={24 * 30}
      fps={30}
      width={1080}
      height={1920}
    />
    <Composition id="SketchDemo" component={SketchDemo} durationInFrames={60} fps={30} width={1080} height={1920} />
    </>
  );
};
