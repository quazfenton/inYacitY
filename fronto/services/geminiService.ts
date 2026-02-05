import { GoogleGenAI, Type } from "@google/genai";
import { Event } from '../types';

const apiKey = process.env.API_KEY || '';
// Initialize AI only if key exists to prevent crash on static view, though logic handles it.
const ai = new GoogleGenAI({ apiKey });

export const generateUndergroundEvents = async (cityName: string): Promise<Event[]> => {
  if (!apiKey) {
    console.warn("No API Key found for Gemini");
    return [];
  }

  const model = "gemini-3-flash-preview";

  try {
    const response = await ai.models.generateContent({
      model,
      contents: `Generate 3 fictional, hyper-specific, underground, hipster/avant-garde events for ${cityName} happening in the next 48 hours. 
      The tone should be mysterious, cool, and exclusive. 
      Think illegal raves, experimental art galleries, pop-up dining in sewers, or drone synth concerts.`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              title: { type: Type.STRING },
              location: { type: Type.STRING },
              date: { type: Type.STRING },
              time: { type: Type.STRING },
              description: { type: Type.STRING },
              tags: { type: Type.ARRAY, items: { type: Type.STRING } },
              price: { type: Type.STRING },
            },
            required: ["title", "location", "date", "time", "description", "tags", "price"]
          }
        }
      }
    });

    const rawEvents = JSON.parse(response.text || "[]");
    
    // Map to our Event interface with IDs
    return rawEvents.map((evt: any, index: number) => ({
      id: `ai-${Date.now()}-${index}`,
      ...evt,
      imageUrl: `https://picsum.photos/600/400?random=${Date.now() + index}`,
      isAiGenerated: true
    }));

  } catch (error) {
    console.error("Failed to generate events:", error);
    return [];
  }
};