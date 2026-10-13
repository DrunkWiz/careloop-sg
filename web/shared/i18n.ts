// UI strings, English and Chinese, from day one. No hard-coded text in components. Owner: Mingyu.
// Singlish speakers see English. Care-app strings go under `care.*` (Nathan).
import { createContext, useContext } from 'react';

export type Lang = 'en' | 'en-SG' | 'zh';
export type UiLang = 'en' | 'zh';

export const uiLang = (lang: Lang): UiLang => (lang === 'zh' ? 'zh' : 'en');
/** BCP-47 tag for the Web Speech API. */
export const speechLang = (lang: Lang): string => (lang === 'zh' ? 'zh-CN' : 'en-SG');

const en = {
  'app.name': 'CareLoop',
  'lang.switch': '中文',
  'common.back': 'Back',
  'common.yes': 'Yes',
  'common.no': 'No',
  'common.save': 'Save',
  'common.send': 'Send',
  'common.cancel': 'Cancel',
  'common.saved': 'Saved. Thank you.',
  'common.offline': 'Cannot reach CareLoop right now. Please try again.',

  'home.greeting.morning': 'Good morning',
  'home.greeting.afternoon': 'Good afternoon',
  'home.greeting.evening': 'Good evening',
  'home.pills': 'Took my pills',
  'home.pills.done': 'Pills taken today',
  'home.bp': 'Log my BP',
  'home.bp.done': 'BP logged today',
  'home.feel': 'How I feel',
  'home.talk': 'Hold to talk',
  'home.knows': 'What CareLoop knows about me',

  'checkin.title': 'Morning check-in',
  'checkin.default': 'How are you feeling today?',
  'checkin.hold': 'Hold the button and talk',
  'checkin.listening': 'Listening…',
  'checkin.release': 'Let go when you finish',
  'checkin.heard': 'I heard:',
  'checkin.type': 'Or type here',
  'checkin.placeholder': 'e.g. Feeling ok, went to the market',
  'checkin.thanks': 'Thank you for telling me.',
  'checkin.noSpeech': 'Voice is not available on this phone. Please type instead.',
  'checkin.micDenied': 'The microphone is blocked. Please allow it, or type instead.',
  'checkin.quick.good': 'I feel good',
  'checkin.quick.ok': 'So-so',
  'checkin.quick.unwell': 'Not feeling well',
  // Canned check-ins the big buttons send. They go through the same understanding as speech.
  'checkin.text.pills': 'Took my pills',
  'checkin.text.good': 'I feel good today',
  'checkin.text.ok': 'Feeling so-so today',
  'checkin.text.unwell': 'Not feeling well today',

  'bp.title': 'Log my BP',
  'bp.top': 'Top number',
  'bp.bottom': 'Bottom number',
  'bp.pulse': 'Pulse (if shown)',
  'bp.hint': 'Copy the numbers from your BP machine.',
  'bp.check': 'Please check the numbers',
  'bp.checkBody': 'The top number is usually bigger than the bottom one. Are these right?',
  'bp.missing': 'Please fill in the top and bottom numbers.',

  'confirm.title': 'Did I hear you right?',
  'confirm.bp': 'Top number {sys}, bottom number {dia}',
  'confirm.pulse': 'Pulse {pulse}',
  'confirm.yes': 'Yes, correct',
  'confirm.no': 'No, let me type it',

  'haze.title': 'Haze today',

  'suggest.title': 'Something you might enjoy',
  'suggest.indoor': 'Indoors',
  'suggest.free': 'Free',
  'suggest.notForMe': 'Not for me',
  'suggest.removed': 'OK, I will remember.',

  'redflag.title': 'Please get help now',
  'redflag.call': 'Call 995',

  'knows.title': 'What CareLoop knows about me',
  'knows.intro': 'This is everything CareLoop remembers about you. Tap Erase to remove anything.',
  'knows.erase': 'Erase',
  'knows.erased': 'Erased.',
  'knows.empty': 'CareLoop does not know anything about you yet.',

  'pair.title': 'Set up CareLoop',
  'pair.intro': 'A family member or your Active Ageing Centre helps set this up.',
  'pair.code': 'Code from the caregiver app',
  'pair.codePlaceholder': '6-digit code',
  'pair.language': 'Language',
  'pair.consent': 'What can CareLoop share with the caregiver?',
  'pair.consent.bp': 'Blood pressure readings',
  'pair.consent.meds': 'Whether medicines were taken',
  'pair.consent.words': 'What I say in check-ins',
  'pair.consent.activity': 'Steps and activity',
  'pair.consent.note': 'You can change this any time. Only the caregiver you link here is told when something needs attention.',
  'pair.submit': 'Link to caregiver',
  'pair.badCode': 'That code did not work. Please check it with your caregiver.',
  'pair.done': 'Linked to {contact}.',

  'demo.banner': 'Demo data: not a real person.',
} as const;

export type StringKey = keyof typeof en;

const zh: Record<StringKey, string> = {
  'app.name': 'CareLoop',
  'lang.switch': 'English',
  'common.back': '返回',
  'common.yes': '是',
  'common.no': '不是',
  'common.save': '保存',
  'common.send': '发送',
  'common.cancel': '取消',
  'common.saved': '已保存，谢谢。',
  'common.offline': '现在连不上 CareLoop，请再试一次。',

  'home.greeting.morning': '早上好',
  'home.greeting.afternoon': '下午好',
  'home.greeting.evening': '晚上好',
  'home.pills': '我吃药了',
  'home.pills.done': '今天已吃药',
  'home.bp': '记录血压',
  'home.bp.done': '今天已量血压',
  'home.feel': '我的感觉',
  'home.talk': '按住说话',
  'home.knows': 'CareLoop 知道我什么',

  'checkin.title': '早上问候',
  'checkin.default': '今天身体怎么样？',
  'checkin.hold': '按住按钮说话',
  'checkin.listening': '正在听…',
  'checkin.release': '说完就放开',
  'checkin.heard': '我听到：',
  'checkin.type': '或者在这里打字',
  'checkin.placeholder': '例如：今天还好，去了巴刹',
  'checkin.thanks': '谢谢您告诉我。',
  'checkin.noSpeech': '这部手机不能用语音，请打字。',
  'checkin.micDenied': '麦克风被关了。请打开，或者打字。',
  'checkin.quick.good': '我很好',
  'checkin.quick.ok': '一般般',
  'checkin.quick.unwell': '不太舒服',
  'checkin.text.pills': '我吃了药',
  'checkin.text.good': '今天感觉很好',
  'checkin.text.ok': '今天一般般',
  'checkin.text.unwell': '今天不太舒服',

  'bp.title': '记录血压',
  'bp.top': '上面的数字（高压）',
  'bp.bottom': '下面的数字（低压）',
  'bp.pulse': '脉搏（如果有）',
  'bp.hint': '照着血压计上的数字填。',
  'bp.check': '请检查数字',
  'bp.checkBody': '上面的数字通常比下面的大。这些数字对吗？',
  'bp.missing': '请填上面和下面的数字。',

  'confirm.title': '我听对了吗？',
  'confirm.bp': '上面 {sys}，下面 {dia}',
  'confirm.pulse': '脉搏 {pulse}',
  'confirm.yes': '对，没错',
  'confirm.no': '不对，我来打字',

  'haze.title': '今天的烟霾',

  'suggest.title': '您可能会喜欢',
  'suggest.indoor': '室内',
  'suggest.free': '免费',
  'suggest.notForMe': '不适合我',
  'suggest.removed': '好的，我记住了。',

  'redflag.title': '请马上求助',
  'redflag.call': '打 995',

  'knows.title': 'CareLoop 知道我什么',
  'knows.intro': '这是 CareLoop 记得的关于您的一切。按“删除”就可以去掉。',
  'knows.erase': '删除',
  'knows.erased': '已删除。',
  'knows.empty': 'CareLoop 还不知道您的任何事。',

  'pair.title': '设置 CareLoop',
  'pair.intro': '请家人或乐龄活动中心帮您设置。',
  'pair.code': '照顾者应用里的号码',
  'pair.codePlaceholder': '6位数号码',
  'pair.language': '语言',
  'pair.consent': 'CareLoop 可以和照顾者分享什么？',
  'pair.consent.bp': '血压读数',
  'pair.consent.meds': '有没有吃药',
  'pair.consent.words': '我在问候里说的话',
  'pair.consent.activity': '步数和活动',
  'pair.consent.note': '您随时可以改。只有在这里连接的照顾者，会在需要注意时收到通知。',
  'pair.submit': '连接照顾者',
  'pair.badCode': '这个号码不行。请和照顾者再核对一下。',
  'pair.done': '已连接到{contact}。',

  'demo.banner': '演示数据：不是真人。',
};

export const strings: Record<UiLang, Record<StringKey, string>> = { en, zh };

export function translate(lang: Lang, key: StringKey, vars?: Record<string, string | number>): string {
  let s = strings[uiLang(lang)][key] ?? strings.en[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  return s;
}

export const LangContext = createContext<Lang>('en');

/** const t = useT(); t('home.pills') */
export function useT() {
  const lang = useContext(LangContext);
  return (key: StringKey, vars?: Record<string, string | number>) => translate(lang, key, vars);
}
