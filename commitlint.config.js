/** @type {import('@commitlint/types').UserConfig} */
export default {
	extends: ['@commitlint/config-conventional'],
	rules: {
		// Allowed types per CLAUDE.md git workflow
		'type-enum': [
			2,
			'always',
			['feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'perf', 'ci', 'style', 'build', 'revert']
		],
		// Body line length not enforced (long descriptions OK)
		'body-max-line-length': [0, 'always'],
		'footer-max-line-length': [0, 'always']
	}
};
