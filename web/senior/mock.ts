// In-browser stand-in for the API, so the senior app runs before the contract freezes.
// Synthetic data only. Its understanding is a toy; the real one is backend/language.
import type { Lang } from '../shared/i18n';
import type { BP, CheckInResult, Consent, Facts, KnownFact, Message, PairResult, Today } from './types';

const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const today = new Date().toDateString();

const state = {
  name: 'Mdm Tan',
  contact: 'Wei Ling',
  lang: 'en' as Lang,
  pillsOn: '',
  bpOn: '',
  feelOn: '',
  hidden: new Set<string>(),
  knows: [
    { id: 'k1', kind: 'condition', text: 'Has high blood pressure' },
    { id: 'k2', kind: 'medicine', text: 'Takes amlodipine 5 mg every morning' },
    { id: 'k3', kind: 'routine', text: 'Usually checks in around 8am' },
    { id: 'k4', kind: 'like', text: 'Likes mahjong and karaoke' },
    { id: 'k5', kind: 'contact', text: 'Daughter Wei Ling is the main contact' },
  ] as KnownFact[],
};

const RED = /chest pain|heart pain|pengsan|faint|slurr|face.*droop|胸口痛|胸痛|晕倒|说话不清|脸歪|嘴歪/i;

function msg(rung: Message['rung'], lang: Lang, text: string): Message {
  return { to: 'senior', rung, language: lang, text, from_template: true, guardrail: { passed: true, reasons: [] }, model: null };
}

function parse(text: string, lang: Lang): Facts {
  const bp: BP[] = [];
  const m = text.match(/(\d{2,3})\s*(?:\/|over|by|除以)\s*(\d{2,3})/i) ?? text.match(/(?:bp|血压)\D{0,10}(\d{2,3})[\s,，]+(\d{2,3})/i);
  if (m) {
    const [sys, dia] = [Number(m[1]), Number(m[2])];
    const keyed = !/[/]|over|by|除以/.test(m[0]);
    const plausible = sys > dia && sys >= 60 && sys <= 280 && dia >= 30 && dia <= 160;
    const confidence = !plausible ? 0.3 : keyed ? 0.75 : 0.95;
    bp.push({ systolic: sys, diastolic: dia, pulse: null, confidence, span: m[0], plausible, needs_confirmation: confidence < 0.8 || !plausible });
  }
  const red = RED.test(text);
  const words = text.match(RED)?.[0] ?? '';
  return {
    lang, bp, pulse: null,
    doses: /took my pills|吃了药|medicine already/i.test(text) ? [{ taken: true, medicine: null, span: text }] : [],
    running_out: [], symptoms: red ? [{ code: 'chest_pain', words, red_flag: true }] : [],
    activities: [], mood: null, english: text, source: 'mock', red_flag: red, feeling_unwell: red, social_contact: false,
  };
}

export const mock = {
  async today(_id: string): Promise<Today> {
    await wait();
    const zh = state.lang === 'zh';
    const hour = new Date().getHours();
    return {
      senior: { id: 'demo-senior', name: state.name, language: state.lang },
      pills_taken: state.pillsOn === today,
      bp_logged: state.bpOn === today,
      feel_logged: state.feelOn === today,
      checkin_due: state.feelOn !== today && hour >= 6 && hour < 12,
      prompt: msg('1', state.lang, zh ? `${state.name}，今天身体怎么样？` : `${state.name}, how are you feeling today?`),
      haze: {
        psi: 112,
        band: 'unhealthy',
        text: zh
          ? '今天空气不好（PSI 101-200）。请减少户外活动，尽量待在室内。'
          : 'The air is unhealthy today (PSI 101-200). Cut down on outdoor activity and stay indoors where you can.',
      },
      suggestions: [
        { id: 's1', place: zh ? 'Kebun Baru 乐龄活动中心：卡拉OK，上午10点' : 'Kebun Baru AAC: karaoke, 10am', why_it_fits: zh ? '您喜欢唱歌' : 'You like singing', indoor: true, free: true, response: null },
        { id: 's2', place: zh ? 'Ang Mo Kio 民众俱乐部：椅子运动' : 'Ang Mo Kio CC: chair exercise', why_it_fits: zh ? '室内，适合今天' : 'Indoors, good for today', indoor: true, free: true, response: null },
        { id: 's3', place: zh ? '宏茂桥图书馆：健康讲座' : 'Ang Mo Kio Library: health talk', why_it_fits: zh ? '离家近' : 'Near your home', indoor: true, free: true, response: null },
      ].filter((s) => !state.hidden.has(s.id)),
    };
  },

  async checkin(_id: string, text: string, lang: Lang): Promise<CheckInResult> {
    await wait(400);
    const facts = parse(text, lang);
    if (facts.doses.some((d) => d.taken)) state.pillsOn = today;
    else state.feelOn = today;
    const zh = lang === 'zh';
    let message: Message | null = null;
    if (facts.red_flag) {
      message = msg('R', lang, zh
        ? `请现在马上打995，或者请身边的人帮您打。您刚才说：“${facts.symptoms[0].words}”。我现在就通知${state.contact}。`
        : `Please call 995 now, or ask someone near you to call. You told me: "${facts.symptoms[0].words}". I am telling ${state.contact} now.`);
    }
    return { checkin_id: `c${Date.now()}`, facts, message };
  },

  async reading(_id: string, _bp: { systolic: number; diastolic: number }) {
    await wait();
    state.bpOn = today;
  },

  async knows(_id: string): Promise<KnownFact[]> {
    await wait();
    return [...state.knows];
  },

  async forget(_id: string, factId: string) {
    await wait();
    state.knows = state.knows.filter((k) => k.id !== factId);
  },

  async notForMe(_id: string, suggestionId: string) {
    await wait();
    state.hidden.add(suggestionId);
  },

  async pair(code: string, lang: Lang, _consent: Consent): Promise<PairResult> {
    await wait(500);
    if (!/^\d{6}$/.test(code)) throw new Error('bad code');
    state.lang = lang;
    return { senior_id: 'demo-senior', contact_name: state.contact, contact_id: 'demo-contact' };
  },

  setLang(lang: Lang) {
    state.lang = lang;
  },
};
