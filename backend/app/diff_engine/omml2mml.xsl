<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
  xmlns="http://www.w3.org/1998/Math/MathML"
  exclude-result-prefixes="m">

<xsl:output method="xml" indent="no" omit-xml-declaration="yes"/>

<!-- Root math elements: block-level (oMathPara) -->
<xsl:template match="m:oMathPara">
  <math display="block">
    <xsl:apply-templates/>
  </math>
</xsl:template>

<!-- Root math elements: inline (oMath) -->
<xsl:template match="m:oMath">
  <math display="inline">
    <xsl:apply-templates/>
  </math>
</xsl:template>

<!-- Run -->
<xsl:template match="m:r">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Text -->
<xsl:template match="m:t">
  <mi><xsl:value-of select="."/></mi>
</xsl:template>

<!-- Fraction -->
<xsl:template match="m:f">
  <mfrac>
    <xsl:apply-templates select="m:num"/>
    <xsl:apply-templates select="m:den"/>
  </mfrac>
</xsl:template>

<!-- Numerator -->
<xsl:template match="m:num">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Denominator -->
<xsl:template match="m:den">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Radical / Square Root -->
<xsl:template match="m:rad">
  <msqrt><xsl:apply-templates/></msqrt>
</xsl:template>

<!-- Degree (for radicals) -->
<xsl:template match="m:deg">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Superscript -->
<xsl:template match="m:sup">
  <msup><xsl:apply-templates/></msup>
</xsl:template>

<!-- Subscript -->
<xsl:template match="m:sub">
  <msub><xsl:apply-templates/></msub>
</xsl:template>

<!-- Accent / Overbar -->
<xsl:template match="m:acc">
  <mover>
    <xsl:apply-templates select="m:e"/>
    <mo><xsl:value-of select="m:chr/@m:val"/></mo>
  </mover>
</xsl:template>

<!-- Bar accent -->
<xsl:template match="m:bar">
  <mover>
    <xsl:apply-templates select="m:e"/>
    <mo stretchy="true">¯</mo>
  </mover>
</xsl:template>

<!-- Base of accented/bar expression -->
<xsl:template match="m:e">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Group character (overbrace, underbrace) -->
<xsl:template match="m:groupChr">
  <mover>
    <xsl:apply-templates select="m:e"/>
    <mo><xsl:value-of select="m:chr/@m:val"/></mo>
  </mover>
</xsl:template>

<!-- N-ary operator (sum, product, integral) -->
<xsl:template match="m:nary">
  <xsl:variable name="chr" select="m:chr/@m:val"/>
  <xsl:choose>
    <xsl:when test="$chr='∑' or $chr='&#x2211;'">
      <munderover>
        <mo>∑</mo>
        <xsl:apply-templates select="m:sub"/>
        <xsl:apply-templates select="m:sup"/>
      </munderover>
    </xsl:when>
    <xsl:when test="$chr='∏' or $chr='&#x220F;'">
      <munderover>
        <mo>∏</mo>
        <xsl:apply-templates select="m:sub"/>
        <xsl:apply-templates select="m:sup"/>
      </munderover>
    </xsl:when>
    <xsl:when test="$chr='∫' or $chr='&#x222B;'">
      <munderover>
        <mo>∫</mo>
        <xsl:apply-templates select="m:sub"/>
        <xsl:apply-templates select="m:sup"/>
      </munderover>
    </xsl:when>
    <xsl:otherwise>
      <mrow>
        <mo><xsl:value-of select="$chr"/></mo>
        <xsl:apply-templates/>
      </mrow>
    </xsl:otherwise>
  </xsl:choose>
</xsl:template>

<!-- Limit -->
<xsl:template match="m:lim">
  <munder><xsl:apply-templates/></munder>
</xsl:template>

<!-- Lower limit of n-ary -->
<xsl:template match="m:sub/*">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Delimiter / Brackets -->
<xsl:template match="m:d">
  <mrow>
    <mo><xsl:value-of select="m:dPr/m:begChr/@m:val"/></mo>
    <xsl:apply-templates select="m:e"/>
    <mo><xsl:value-of select="m:dPr/m:endChr/@m:val"/></mo>
  </mrow>
</xsl:template>

<!-- Matrix -->
<xsl:template match="m:m">
  <mtable>
    <xsl:for-each select="m:mr">
      <mtr>
        <xsl:for-each select="m:e">
          <mtd><mrow><xsl:apply-templates/></mrow></mtd>
        </xsl:for-each>
      </mtr>
    </xsl:for-each>
  </mtable>
</xsl:template>

<!-- Matrix row -->
<xsl:template match="m:mr">
  <mtr><xsl:apply-templates/></mtr>
</xsl:template>

<!-- Phantom / spacing -->
<xsl:template match="m:phant">
  <mphantom><xsl:apply-templates/></mphantom>
</xsl:template>

<!-- Box -->
<xsl:template match="m:box">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Function (sin, cos, etc.) -->
<xsl:template match="m:func">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

<!-- Function name -->
<xsl:template match="m:fName">
  <mi><xsl:apply-templates/></mi>
</xsl:template>

<!-- Scripts (pre-sub-sup) -->
<xsl:template match="m:sPre">
  <mmultiscripts>
    <xsl:apply-templates select="m:e"/>
    <mprescripts/>
    <xsl:apply-templates select="m:sub"/>
    <xsl:apply-templates select="m:sup"/>
  </mmultiscripts>
</xsl:template>

<!-- sSub / sSup wrappers -->
<xsl:template match="m:sSub">
  <msub><xsl:apply-templates/></msub>
</xsl:template>
<xsl:template match="m:sSup">
  <msup><xsl:apply-templates/></msup>
</xsl:template>

<!-- Fallback: copy text content -->
<xsl:template match="text()">
  <xsl:value-of select="."/>
</xsl:template>

<!-- Ignore properties -->
<xsl:template match="m:dPr|m:accPr|m:barPr|m:naryPr|m:radPr|m:fPr|m:rPr|m:sPrePr|m:mPr|m:ctrlPr|m:eqArrPr|m:groupChrPr|m:limLowPr|m:borderBoxPr"/>

<!-- Ignore control characters -->
<xsl:template match="m:ctrlPr"/>

<!-- Catch-all: copy children -->
<xsl:template match="*">
  <mrow><xsl:apply-templates/></mrow>
</xsl:template>

</xsl:stylesheet>
