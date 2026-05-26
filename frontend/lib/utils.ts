/** クラス名を空白区切りで結合(falsy を捨てる)。 */
export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ');
}
