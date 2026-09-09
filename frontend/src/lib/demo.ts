export interface Profile {
  name: string;
  age: number;
  city: string;
  goal: string;
  rhythm: string;
  interests: string[];
  companionship: string;
  note: string;
}

export interface Candidate {
  id: number;
  name: string;
  age: number;
  city: string;
  occupation: string;
  interests: string[];
  color: string;
  quote: string;
  rhythm: string;
  companionship: string;
  budget: number;
  food: string;
  detail: string;
}

export const exampleProfile: Profile = {
  name: "小予",
  age: 23,
  city: "杭州",
  goal: "认真长久",
  rhythm: "规律慢生活",
  interests: ["咖啡", "电影", "散步"],
  companionship: "每周 2–3 次",
  note: "喜欢不赶时间的周末。希望可以一起探索小店，也能舒服地各做各的事。",
};

export const interestOptions = [
  "咖啡",
  "电影",
  "散步",
  "摄影",
  "阅读",
  "旅行",
  "音乐",
  "运动",
  "看展",
  "游戏",
];

export interface PlanItem {
  time: string;
  title: string;
  detail: string;
  cost: number;
  kind: "food" | "walk" | "coffee";
}
