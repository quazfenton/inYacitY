export interface Event {
  id: string;
  title: string;
  location: string;
  date: string;
  time: string;
  description: string;
  tags: string[];
  price: string;
  imageUrl?: string;
  isAiGenerated?: boolean;
  link?: string;
  source?: string;
}

export interface City {
  id: string;
  name: string;
  slug: string;
  coordinates: {
    lat: number;
    lng: number;
  };
}

export enum ViewState {
  LANDING = 'LANDING',
  CITY_FEED = 'CITY_FEED',
}

export interface VibeData {
  day: string;
  intensity: number;
  crowd: number;
}