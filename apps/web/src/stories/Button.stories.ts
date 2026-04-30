import type { Meta, StoryObj } from '@storybook/sveltekit';
import ButtonDemo from './ButtonDemo.svelte';

/**
 * 모아오더 기본 버튼 컴포넌트입니다. shadcn-svelte 기반 + Toss TDS 스타일 차용.
 *
 * ## TDS prop 매핑
 *
 * | TDS (React Native) | 모아오더 (shadcn-svelte) | 비고 |
 * |---|---|---|
 * | `type` (primary/danger/light/dark) | `variant` (default/destructive/outline/secondary) | 시각 강조 |
 * | `style` (fill/weak) | `variant`에 통합 (outline/ghost = weak) | 시각 강도 |
 * | `display` (block/full) | `class="w-full"` 또는 부모 레이아웃 | 너비 |
 * | `size` (tiny/medium/large/big) | `size` (xs/sm/default/lg) | 크기 |
 * | `loading` | `loading` ✓ | 동일 |
 * | `disabled` | `disabled` ✓ | 동일 |
 * | `leftAccessory` | children 슬롯에 직접 작성 | 아이콘 |
 *
 * ## 로딩 패턴 (Toss 스타일)
 *
 * `loading=true` 일 때 텍스트는 숨겨지고 스피너만 중앙에 표시됩니다.
 * 버튼 너비는 텍스트 공간을 그대로 유지해서 클릭 후 흔들림 없음.
 *
 * 스피너 형태는 `spinner` prop으로 선택 (기본값 `dots`).
 */
const meta = {
	title: '컴포넌트/Button',
	component: ButtonDemo,
	tags: ['autodocs'],
	argTypes: {
		label: {
			control: 'text',
			description: '버튼 텍스트',
		},
		variant: {
			control: 'select',
			options: ['default', 'outline', 'secondary', 'ghost', 'destructive', 'link'],
			description: '버튼 스타일 변형 (TDS의 type + style 역할)',
			table: { defaultValue: { summary: 'default' } },
		},
		size: {
			control: 'select',
			options: ['default', 'sm', 'lg', 'xs', 'icon', 'icon-xs', 'icon-sm', 'icon-lg'],
			description: '버튼 크기 (TDS의 size 역할)',
			table: { defaultValue: { summary: 'default' } },
		},
		loading: {
			control: 'boolean',
			description: '로딩 상태. true면 텍스트 숨기고 스피너만 표시',
			table: { defaultValue: { summary: 'false' } },
		},
		spinner: {
			control: 'inline-radio',
			options: ['ring', 'dots', 'bars'],
			description: '스피너 형태 (loading 시에만 표시)',
			table: { defaultValue: { summary: 'dots' } },
		},
		disabled: {
			control: 'boolean',
			description: '비활성화 상태',
		},
	},
	args: {
		label: '주문하기',
		variant: 'default',
		size: 'default',
		loading: false,
		spinner: 'dots',
		disabled: false,
	},
} satisfies Meta<typeof ButtonDemo>;

export default meta;
type Story = StoryObj<typeof meta>;

// === Variants (TDS의 type + style) ===

/** 기본 — 가장 강조해야 할 주요 액션. (TDS `type=primary`, `style=fill`) */
export const Primary: Story = {
	name: 'Primary (주요 액션)',
	args: { variant: 'default', label: '공동구매 참여하기' },
};

/** 외곽선 — 보조 액션, 취소 등. (TDS `type=light`, `style=weak`) */
export const Outline: Story = {
	name: 'Outline (보조 액션)',
	args: { variant: 'outline', label: '뒤로가기' },
};

/** 보조 — 본문 내 보조 CTA. (TDS `type=light`, `style=fill`) */
export const Secondary: Story = {
	name: 'Secondary (옅은 강조)',
	args: { variant: 'secondary', label: '더보기' },
};

/** 유령 — 배경 없음, 아이콘 버튼/메뉴 등. (TDS `type=light`, `style=weak`) */
export const Ghost: Story = {
	name: 'Ghost (배경 없음)',
	args: { variant: 'ghost', label: '닫기' },
};

/** 위험 — 삭제·취소 같은 파괴적 액션. (TDS `type=danger`) */
export const Destructive: Story = {
	name: 'Destructive (위험 액션)',
	args: { variant: 'destructive', label: '주문 삭제' },
};

/** 링크 — 텍스트 링크 형태. */
export const Link: Story = {
	name: 'Link',
	args: { variant: 'link', label: '자세히 보기' },
};

// === Sizes (TDS의 size) ===

export const SizeXS: Story = {
	name: 'Size: xs (= TDS tiny)',
	args: { size: 'xs', label: '태그' },
};

export const SizeSM: Story = {
	name: 'Size: sm',
	args: { size: 'sm', label: '필터' },
};

export const SizeDefault: Story = {
	name: 'Size: default (= TDS medium)',
	args: { size: 'default', label: '확인' },
};

export const SizeLG: Story = {
	name: 'Size: lg (= TDS big)',
	args: { size: 'lg', label: '결제하기' },
};

// === States ===

/** 로딩 중 — 텍스트 숨기고 스피너만 표시 (Toss 패턴) */
export const Loading: Story = {
	name: '로딩 중',
	args: { loading: true, label: '결제하기', spinner: 'dots' },
};

/** 비활성화 — 클릭 불가, 시각적으로 약하게 */
export const Disabled: Story = {
	name: '비활성화',
	args: { disabled: true, label: '마감된 공구' },
};

// === Spinner Variants ===

/** 스피너 형태: dots (기본) — 가벼운 작업, friendly */
export const SpinnerDots: Story = {
	name: '스피너: dots',
	args: { loading: true, spinner: 'dots', label: '결제하기' },
};

/** 스피너 형태: ring — 표준 회전형, Toss/Material 스타일 */
export const SpinnerRing: Story = {
	name: '스피너: ring',
	args: { loading: true, spinner: 'ring', label: '결제하기' },
};

/** 스피너 형태: bars — 데이터 로드/처리 중 인상 */
export const SpinnerBars: Story = {
	name: '스피너: bars',
	args: { loading: true, spinner: 'bars', label: '결제하기' },
};
